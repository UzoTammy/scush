import datetime
from django.dispatch import receiver
from django.db.models import Sum
from django.db.models.signals import post_save
from django.core.mail import EmailMessage
from django.template import loader
from .models import BalanceSheet, Money, TradeDaily
from djmoney.models.fields import Money



@receiver(post_save, sender=TradeDaily)
def trade_daily_create(sender, instance, created, **kwargs):
    if created:
        head_title = 'Created'
        qs = TradeDaily.objects.filter(date__year=instance.date.year, date__month=instance.date.month)
    else:
        head_title = 'Updated'
        qs = TradeDaily.objects.filter(date__range=(datetime.date(instance.date.year, instance.date.month, 1), instance.date))

    qs_all = TradeDaily.objects.all()

    net_profit = instance.gross_profit - instance.indirect_expenses
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
            'net_profit': net_profit,

            'margin_ratio': round(100*net_profit/instance.sales, 2),
            'delivery_expenses_ratio': 
            round(100*instance.direct_expenses/instance.purchase, 2) 
            if instance.purchase > Money(0, 'NGN') else "Nil",
            'admin_expenses_ratio': 
            round(100*instance.indirect_expenses/instance.sales, 2) 
            if instance.sales > Money(0, 'NGN') else "Nil",

            'total_sales': Money(qs.aggregate(Sum('sales'))['sales__sum'], 'NGN'),
            'total_purchase': Money(qs.aggregate(Sum('purchase'))['purchase__sum'], 'NGN'),
            'total_direct_expenses': Money(qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'], 'NGN'),
            'total_indirect_expenses': Money(qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'], 'NGN'),
            'opening_stock': qs.first().opening_value,
            'total_gross_profit': Money(qs.aggregate(Sum('gross_profit'))['gross_profit__sum'], 'NGN'),
            'total_direct_income': Money(qs.aggregate(Sum('direct_income'))['direct_income__sum'], 'NGN'),
            'total_indirect_income': Money(qs.aggregate(Sum('indirect_income'))['indirect_income__sum'], 'NGN'),
            
            'sales_drive': qs_all.order_by('-pk')[:5],
        } 
    
    total_net_profit = dataset['total_gross_profit'] - dataset['total_indirect_expenses']
    
    total_ratio = {
        'net_profit': total_net_profit,
        'margin_ratio': round(100*total_net_profit/dataset['total_sales'], 2),
        'delivery_expenses_ratio': 
        round(100*dataset['total_indirect_expenses']/dataset['total_purchase'], 2) 
        if dataset['total_purchase'] > Money(0, 'NGN') else "Nil",
        'admin_expenses_ratio': 
        round(100*dataset['total_direct_expenses']/dataset['total_sales'], 2) 
        if dataset['total_sales']>Money(0, 'NGN') else "Nil",
    }

    email = EmailMessage(
        subject=f'Daily P & L Report for {instance.date.strftime("%B, %Y")}',
        body=loader.render_to_string('trade/mail_daily_PL.html', context={'object': dataset, 'ratio': total_ratio, 'head_title': head_title}),
        from_email='',
        to=['uzo.nwokoro@ozonefl.com'],
        cc=['dickson.abanum@ozonefl.com'],
        headers={'message-id': 'zebra'},
    )
    email.content_subtype="html"
    email.send(fail_silently=False)


@receiver(post_save, sender=BalanceSheet)
def bs_mail_sender(sender, instance, created, **kwargs):
    if created:
        head_title = 'Created'
    else:
        head_title = 'Updated'

    email = EmailMessage(
        subject=f'Balance Sheet As At {instance.date.strftime("%B, %Y")}',
        body = loader.render_to_string('trade/mail_bs.html', context={'object': instance, 'head_title': head_title}),
        from_email='',
        to=['uzo.nwokoro@ozonefl.com'],
        cc=['dickson.abanum@ozonefl.com'],
        headers={'message-id': 'tiger'}
    )
    email.content_subtype='html'
    email.send(fail_silently=False)


