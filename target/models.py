from email.policy import default
from django.db import models
from djmoney.models.fields import Money, MoneyField
from django.db import models
import datetime
from django.utils import timezone
from django.urls import reverse
from outlet.models import SalesCenter
from django.core.validators import MaxValueValidator, MinValueValidator


class Sales(models.Model):
    today = datetime.date.today()
    period = models.CharField(max_length=7, default=f'{today.year}-{str(today.month).zfill(2)}')
    date_created = models.DateField(default=timezone.now)
    target = MoneyField(max_digits=12, default_currency='NGN', decimal_places=2)
    achieved = MoneyField(max_digits=12, default_currency='NGN', decimal_places=2)
    sales_center = models.ForeignKey(SalesCenter, on_delete=models.CASCADE, default=1)
    
    
    def __str__(self):
        return f'{self.sales_center} {self.period}'

    def get_absolute_url(self):
        return reverse('sales-detail', kwargs={'pk': self.pk})

class PositionKPIMonthly(models.Model):
    year = models.PositiveSmallIntegerField(default=datetime.date.today().year, validators=[
        MinValueValidator(2021), MaxValueValidator(2040),
    ])
    month = models.PositiveSmallIntegerField(default=datetime.date.today().month, validators=[
        MinValueValidator(1), MaxValueValidator(12),
    ])
    growth = models.PositiveSmallIntegerField()
    margin = models.PositiveSmallIntegerField()
    sales = models.PositiveSmallIntegerField()
    delivery = models.PositiveSmallIntegerField()
    admin = models.PositiveSmallIntegerField()
    man_hour = models.PositiveSmallIntegerField()
    wf_productivity = models.PositiveSmallIntegerField()
    mail_sent_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"{datetime.date(self.year, self.month, 1).strftime('%B, %Y')} KPI Target" 
    






