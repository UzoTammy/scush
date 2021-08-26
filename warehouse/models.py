import datetime
from django.urls import reverse
from django.db import models
from djmoney.models.fields import MoneyField
from django.utils import timezone


class ActiveStoreManager(models.Manager):
    """"To work those stores that are not disabled"""
    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)


class Stores(models.Model):
    today = datetime.date.today()
    TYPES = [('Lock-up', 'Lock-up'), ('Suite', 'Suite'), ('Warehouse', 'Warehouse'), ('Apartment', 'Apartment')]
    USAGE = [('Storage', 'Storage'), ('Sell-out', 'Sell-out'), ('Office', 'Office'), ('Quarters', 'Quarters')]
    name = models.CharField(max_length=50)
    store_type = models.CharField(max_length=30, choices=TYPES)
    usage = models.CharField(max_length=30, choices=USAGE)
    owner = models.CharField(max_length=50, default='Self')
    address = models.CharField(max_length=100)
    contact = models.CharField(max_length=11)
    rent_amount = MoneyField(max_digits=10,
                             decimal_places=2,
                             default_currency='NGN'
                             )
    capacity = models.IntegerField(help_text='33cl Can cases store can take')
    expiry_date = models.DateField(default=timezone.now)
    status = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)

    active = ActiveStoreManager()
    objects = models.Manager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('warehouse-detail', kwargs={'pk': self.pk})


class Renewal(models.Model):
    store = models.ForeignKey(Stores, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    amount_paid = MoneyField(max_digits=10,
                             decimal_places=2,
                             default_currency='NGN')
    expiry_date = models.DateField()
