from stock.models import ProductExtension


def latest_stock_date(request):
    """Expose the date of the most recent stock record for display in the navbar."""
    record = ProductExtension.objects.order_by('-date').first()
    return {'latest_stock_date': record.date if record else None}
