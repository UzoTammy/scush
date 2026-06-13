"""Parsing and validation helpers for the daily "Stock Status" CSV import.

Accepts the raw POS export as-is (no manual header editing required).
Columns are mapped by position - the header text is only used for an
informational warning, never to decide where data lives.
"""
import csv
import io
import re
import datetime
from decimal import Decimal, InvalidOperation

from stock.models import Product, ProductExtension

# "From 12-6-2026 to 12-6-2026" - we want the closing ("to") date.
STOCK_STATUS_DATE_RE = re.compile(
    r'From\s+(\d{1,2}-\d{1,2}-\d{4})\s+to\s+(\d{1,2}-\d{1,2}-\d{4})',
    re.IGNORECASE,
)

EXPECTED_HEADERS = [
    'item details', 'item name', 'qty. out', 'avg. price',
    'amt. out', 'cl. qty', 'price',
]

MIN_COLUMNS = 7


def decode_csv_bytes(raw_bytes):
    """Decode raw uploaded bytes, tolerating the encodings POS software tends to emit."""
    for encoding in ('utf-8-sig', 'cp1252'):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode('latin-1', errors='replace')


def parse_money(value):
    """Parse a money/quantity cell such as '12,974.00', '"2,701"' or '0' into a Decimal."""
    text = (value or '').strip().strip('"').replace(',', '').strip()
    if text == '':
        return Decimal('0')
    return Decimal(text)


def parse_quantity(value):
    """Parse a whole-number cell, tolerating thousands separators and '.00' suffixes."""
    return int(parse_money(value))


def parse_stock_status_csv(raw_bytes):
    """Parse a Stock Status CSV export (raw or hand-edited) into a validation report.

    Returns a dict with:
        error: fatal error message, or None if parsing succeeded
        date: ISO date string of the stock record (the "to" date)
        header_warning: informational message if the header row doesn't look as expected
        valid_rows: list of dicts ready for ProductExtension.update_or_create
        errors: list of {row_number, code, name, reason} for skipped rows
        will_create / will_update: counts of valid rows by outcome
    """
    text = decode_csv_bytes(raw_bytes)
    rows = list(csv.reader(io.StringIO(text)))

    if len(rows) < 6:
        return {'error': 'File is too short to be a Stock Status export.'}

    date_match = STOCK_STATUS_DATE_RE.search(' '.join(rows[2]))
    if not date_match:
        return {'error': 'Could not find the "From DD-MM-YYYY to DD-MM-YYYY" line on row 3.'}
    try:
        record_date = datetime.datetime.strptime(date_match.group(2), '%d-%m-%Y').date()
    except ValueError:
        return {'error': f'Could not parse date "{date_match.group(2)}" from row 3.'}

    header = rows[4]
    if len(header) < MIN_COLUMNS:
        return {'error': f'Header row 5 has fewer than {MIN_COLUMNS} columns.'}

    header_warning = None
    normalized = [cell.strip().lower() for cell in header[:MIN_COLUMNS]]
    if normalized != EXPECTED_HEADERS:
        header_warning = (
            "Header row doesn't match the expected Stock Status column names, "
            "but columns are read by position so this is informational only."
        )

    active_products = set(Product.objects.filter(active=True).values_list('pk', flat=True))
    existing_dates = set(
        ProductExtension.objects.filter(date=record_date).values_list('product_id', flat=True)
    )

    valid_rows = []
    errors = []
    for offset, row in enumerate(rows[5:]):
        row_number = offset + 6
        if not row or row[0].strip() == '':
            continue  # Totals row / blank line
        if len(row) < MIN_COLUMNS:
            errors.append({
                'row_number': row_number, 'code': row[0].strip(), 'name': '',
                'reason': f'Row has fewer than {MIN_COLUMNS} columns.',
            })
            continue

        name = row[1].strip()
        try:
            product_id = int(parse_money(row[0]))
        except InvalidOperation:
            errors.append({
                'row_number': row_number, 'code': row[0].strip(), 'name': name,
                'reason': 'Product code is not a number.',
            })
            continue
        if product_id not in active_products:
            errors.append({
                'row_number': row_number, 'code': str(product_id), 'name': name,
                'reason': 'Product code does not match an active product.',
            })
            continue

        try:
            sell_out = parse_quantity(row[2])
            selling_price = parse_money(row[3])
            sales_amount = parse_money(row[4])
            stock_value = parse_quantity(row[5])
            cost_price = parse_money(row[6])
        except InvalidOperation:
            errors.append({
                'row_number': row_number, 'code': str(product_id), 'name': name,
                'reason': 'One or more numeric fields could not be parsed.',
            })
            continue

        valid_rows.append({
            'row_number': row_number,
            'product_id': product_id,
            'name': name,
            'sell_out': sell_out,
            'selling_price': str(selling_price),
            'sales_amount': str(sales_amount),
            'stock_value': stock_value,
            'cost_price': str(cost_price),
            'will_update': product_id in existing_dates,
        })

    will_update = sum(1 for row in valid_rows if row['will_update'])
    return {
        'error': None,
        'date': record_date.isoformat(),
        'header_warning': header_warning,
        'valid_rows': valid_rows,
        'errors': errors,
        'will_create': len(valid_rows) - will_update,
        'will_update': will_update,
    }
