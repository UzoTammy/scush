from django.db import models
from djmoney.models.fields import MoneyField, Money
from datetime import date
from django.urls.base import reverse



class TradeMonthly(models.Model):
    period = models.CharField(max_length=20, 
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
    expenses = MoneyField(max_digits=12, decimal_places=2)
    opening_value = MoneyField(max_digits=12, decimal_places=2)
    closing_value = MoneyField(max_digits=12, decimal_places=2)
    gross_profit = MoneyField(max_digits=12, decimal_places=2)
    

    def __str__(self):
        return f'{self.period}, {self.year}'

    def get_absolute_url(self):
        return reverse('trade-detail', kwargs={'pk': self.pk})