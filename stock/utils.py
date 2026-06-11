import datetime

from django.db.models import Avg

from .models import ProductExtension


def average_sellout(product, days):
    """Average daily sell-out for a product over the last `days` days of recorded
    ProductExtension history (relative to the latest recorded date, not today)."""
    latest = ProductExtension.objects.filter(product=product).order_by('-date').first()
    if latest is None:
        return None

    start_date = latest.date - datetime.timedelta(days=days - 1)
    qs = ProductExtension.objects.filter(product=product, date__range=[start_date, latest.date])
    return qs.aggregate(Avg('sell_out'))['sell_out__avg']


def days_of_cover(current_stock, avg_daily_sellout):
    """How many days the current stock will last at the given average daily sell-out rate."""
    if not avg_daily_sellout or current_stock is None:
        return None
    return current_stock / avg_daily_sellout
