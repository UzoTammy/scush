from django.dispatch import receiver
from django.db.models import Sum
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.template import loader
from .models import Money, TradeDaily
from pdf.views import Ozone


@receiver(post_save, sender=TradeDaily)
def trade_daily_create(sender, instance, created, **kwargs):
    if created:
        head_title = 'Created'
    else:
        head_title = 'Updated'

    qs = TradeDaily.objects.filter(date__year=instance.date.year, date__month=instance.date.month)
    qs_all = TradeDaily.objects.all()

    dataset = {
            'date': instance.date,
            'title': 'P & L',
            'sales': instance.sales,
            'purchase': instance.purchase,
            'direct_expenses': instance.direct_expenses,
            'indirect_expenses': instance.indirect_expenses,
            'opening_value': instance.opening_value,
            'closing_value': instance.closing_value,
            'gross_profit': instance.gross_profit,
            'direct_income': instance.direct_income,
            'indirect_income': instance.indirect_income,
            'net_profit': instance.gross_profit - instance.indirect_expenses,

            'total_sales': Money(qs.aggregate(Sum('sales'))['sales__sum'], 'NGN'),
            'total_purchase': Money(qs.aggregate(Sum('purchase'))['purchase__sum'], 'NGN'),
            'total_direct_expenses': Money(qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'], 'NGN'),
            'total_indirect_expenses': Money(qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'], 'NGN'),
            'opening_stock': qs.first().opening_value,
            'total_gross_profit': Money(qs.aggregate(Sum('gross_profit'))['gross_profit__sum'], 'NGN'),
            'total_direct_income': Money(qs.aggregate(Sum('direct_income'))['direct_income__sum'], 'NGN'),
            'total_indirect_income': Money(qs.aggregate(Sum('indirect_income'))['indirect_income__sum'], 'NGN'),
            'sales_drive': qs_all.order_by('-pk')[:5],
            'logo_image': Ozone.logo()
        } 
    email = EmailMessage(
        subject=f'Daily P & L Report for {instance.date} - {head_title}',
        body=loader.render_to_string('trade/mail_daily_PL.html', context={'object': dataset}),
        from_email='',
        to=['uzo.nwokoro@ozonefl.com'],
        cc=['dickson.abanum@ozonefl.com'],
        headers={'message-id': 'zebra'},
    )
    email.content_subtype="html"
    email.send(fail_silently=False)





