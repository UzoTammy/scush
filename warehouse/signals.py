import datetime
from django.dispatch import receiver, Signal


signal_renew_store = Signal()

@receiver(signal_renew_store)
def update_store(sender, instance, **kwargs):
    extra_data = kwargs.get('extra_data')
    instance.status = True
    if instance.expiry_date.month + extra_data.get('month') > 12:
        month = instance.expiry_date.month + extra_data.get('month') - 12
        year = instance.expiry_date.year + extra_data.get('year') + 1
    else:
        month = instance.expiry_date.month + extra_data.get('month')
        year = instance.expiry_date.year + extra_data.get('year')
    instance.expiry_date = datetime.date(year, month, instance.expiry_date.day)
    instance.save()
        
