import math
from django.db import migrations
from django.db.models import Avg


LEAD_TIMES = {
    'Guinness': 7,
    'IB':       7,
    'Monument': 7,
    'NB':       5,
    'Others':   7,
    'Empties':  0,
}

SAFETY_DAYS = 3
REORDER_CYCLE_DAYS = 14

# Suppliers being merged into Guinness
MERGE_FROM = ['GN', 'GN LCO', 'MSS', 'IPS']


def _average_sellout(ProductExtension, product_id, days):
    """Inline version of stock.utils.average_sellout — avoids importing app code."""
    from django.db.models import Max
    latest = (ProductExtension.objects
              .filter(product_id=product_id)
              .aggregate(d=Max('date'))['d'])
    if not latest:
        return 0
    from datetime import timedelta
    cutoff = latest - timedelta(days=days)
    result = (ProductExtension.objects
              .filter(product_id=product_id, date__gte=cutoff)
              .aggregate(avg=Avg('sell_out'))['avg'])
    return result or 0


def apply_changes(apps, schema_editor):
    Source = apps.get_model('stock', 'Source')
    Product = apps.get_model('stock', 'Product')
    ProductExtension = apps.get_model('stock', 'ProductExtension')

    # 1. Set lead times on existing suppliers that are staying
    for code, days in LEAD_TIMES.items():
        Source.objects.filter(code=code).update(lead_time_days=days)

    # 2. Create the merged Guinness supplier
    guinness, _ = Source.objects.get_or_create(
        code='Guinness',
        defaults={'label': 'Guinness', 'lead_time_days': 7, 'active': True},
    )

    # 3. Reassign all products from the four old suppliers to Guinness
    Product.objects.filter(source__code__in=MERGE_FROM).update(source=guinness)

    # 4. Delete the old supplier records
    Source.objects.filter(code__in=MERGE_FROM).delete()

    # 5. Build a lead-time lookup: product_id -> lead_time_days
    lead_map = {
        s.code: s.lead_time_days
        for s in Source.objects.all()
    }

    # 6. Calculate and save stock parameters for all active products
    to_update = []
    for p in Product.objects.filter(active=True).exclude(source__code='Empties').select_related('source'):
        avg = _average_sellout(ProductExtension, p.pk, 90)
        if avg == 0:
            avg = _average_sellout(ProductExtension, p.pk, 30)
        if avg == 0:
            continue

        src_code = p.source.code if p.source else 'Others'
        lead = lead_map.get(src_code, 7)

        p.min_stock_level = math.ceil(avg * SAFETY_DAYS)
        p.reorder_point   = math.ceil(avg * (lead + SAFETY_DAYS))
        p.reorder_qty     = math.ceil(avg * REORDER_CYCLE_DAYS)
        p.max_stock_level = p.reorder_point + p.reorder_qty
        to_update.append(p)

    Product.objects.bulk_update(
        to_update,
        ['min_stock_level', 'reorder_point', 'reorder_qty', 'max_stock_level'],
    )


def reverse_changes(apps, schema_editor):
    # Intentionally non-reversible: recreating the original supplier split
    # from a merged state is ambiguous. Roll back by restoring a database
    # backup taken before this migration was applied.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0028_stocklocation_branch_code'),
    ]

    operations = [
        migrations.RunPython(apply_changes, reverse_changes),
    ]
