import datetime
from django.urls import reverse
from django.db import models
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from django.utils import timezone



class ActiveStoreManager(models.Manager):
    """"To work those stores that are not disabled"""
    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)

class ActiveBankAccountManager(models.Manager):
    """"To work those stores that are not disabled"""
    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)


class Stores(models.Model):
    today = datetime.date.today()
    TYPES = [('Lock-up', 'Lock-up'), ('Suite', 'Suite'), ('Warehouse', 'Warehouse'), ('Quarters', 'Quarters')]
    USAGE = [('Storage', 'Storage'), ('Sell-out', 'Sell-out'), ('Office', 'Office'), ('Apartment', 'Apartment')]
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
    allocated_levy_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', default=Money(0, 'NGN'))
    capacity = models.IntegerField(help_text='How many 33cl Cans?')
    expiry_date = models.DateField(default=timezone.now)
    status = models.BooleanField(default=False)  # paid & not paid
    disabled = models.BooleanField(default=False)  # quit & still in use

    objects = models.Manager()
    active = ActiveStoreManager()
    
    class Meta:
        verbose_name_plural = 'Stores'


    def __str__(self):
        return f'Store {self.name}'

    def get_absolute_url(self):
        return reverse('warehouse-detail', kwargs={'pk': self.pk})

class StoreLevy(models.Model):
    store = models.ForeignKey(Stores, on_delete=models.CASCADE)
    amount_paid = MoneyField(max_digits=7, decimal_places=2, default_currency='NGN')
    payment_date = models.DateField(default=timezone.now)
    party = models.CharField(max_length=30, verbose_name='Payable To')
    payment_in_full = models.BooleanField(default=True, verbose_name='Full or Part Payment')
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name='Remarks')

    def __str__(self) -> str:
        return f'Levy {self.store.name}'
    
class Renewal(models.Model):
    store = models.ForeignKey(Stores, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now) # date paid
    amount_paid = MoneyField(max_digits=10,
                             decimal_places=2,
                             default_currency='NGN')
    
    class Meta:
        verbose_name_plural = 'Renewal'
        
    def __str__(self):
        return f'{self.store.name}-{self.date}'


class BankAccount(models.Model):
    store = models.OneToOneField(Stores, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    account_number = models.CharField(max_length=10)
    bank = models.CharField(max_length=30)
    disabled = models.BooleanField(default=False)

    def __str__(self):
        return self.store

    def get_absolute_url(self):
         return reverse('warehouse-bank-detail', kwargs={'pk': self.pk})

    objects = models.Manager()
    active = ActiveBankAccountManager()
    