from django.db import models
from djmoney.models.fields import MoneyField, Money
from datetime import date, timezone
from django.urls.base import reverse
from djmoney.models.validators import MinMoneyValidator



class TradeMonthly(models.Model):
    month = models.CharField(max_length=20, 
            choices=[
                ('January', 'January'),
                ('February', 'February'),
                ('March', 'March'),
                ('April', 'April'),
                ('May', 'May'),
                ('June', 'June'),
                ('July', 'July'),
                ('August', 'August'),
                ('September', 'September'),
                ('October', 'October'),
                ('November', 'November'),
                ('December', 'December'), 
                ]
            )
    year = models.PositiveSmallIntegerField(default=date.today().year, choices=[(date.today().year-1, str(date.today().year-1)), 
                                                                                (date.today().year, str(date.today().year)), 
                                                                                (date.today().year+1, str(date.today().year+1))])
    sales = MoneyField(max_digits=12, decimal_places=2)
    purchase = MoneyField(max_digits=12, decimal_places=2)
    direct_expenses = MoneyField(max_digits=12, decimal_places=2)
    indirect_expenses = MoneyField(max_digits=12, decimal_places=2)
    opening_value = MoneyField(max_digits=12, decimal_places=2)
    closing_value = MoneyField(max_digits=12, decimal_places=2)
    gross_profit = MoneyField(max_digits=12, decimal_places=2)
    direct_income = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    indirect_income = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))

    class Meta:
        verbose_name_plural = 'Monthly'


    def __str__(self):
        return f'{self.month}, {self.year}'

    def get_absolute_url(self):
        return reverse('trade-detail', kwargs={'pk': self.pk})


class TradeDaily(models.Model):
    date = models.DateField(default=date.today)
    sales = MoneyField(max_digits=12, decimal_places=2)
    purchase = MoneyField(max_digits=12, decimal_places=2)
    direct_expenses = MoneyField(max_digits=12, decimal_places=2)
    indirect_expenses = MoneyField(max_digits=12, decimal_places=2)
    opening_value = MoneyField(max_digits=12, decimal_places=2)
    closing_value = MoneyField(max_digits=12, decimal_places=2)
    gross_profit = MoneyField(max_digits=12, decimal_places=2)
    direct_income = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    indirect_income = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))

    class Meta:
        verbose_name_plural = 'Daily'
        

    def __str__(self):
        return f'{self.date}'

    def get_absolute_url(self):
        return reverse('trade-daily-detail', kwargs={'pk': self.pk})