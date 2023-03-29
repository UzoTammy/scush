from decimal import Decimal
from django.db import models
from djmoney.models.fields import MoneyField, Money
from django.urls.base import reverse
from datetime import date
from django.utils import timezone


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
        return f'P&L-{self.date}'

    def get_absolute_url(self):
        return reverse('trade-daily-detail', kwargs={'pk': self.pk})

    
    def margin_ratio(self):
        if self.sales > Money(0, 'NGN'):
            return round(100*(self.gross_profit - self.indirect_expenses)/self.sales, 2)
        return Decimal('0')

    def delivery_expense_ratio(self):
        if self.purchase > Money(0, 'NGN'):
            return round(100*self.direct_expenses/self.purchase, 3)    
        return Decimal('0')

    def admin_expense_ratio(self):
        if self.sales > Money(0, 'NGN'):
            return round(100*self.indirect_expenses/self.sales, 3)
        return Decimal('0')
    
    
class BalanceSheet(models.Model):
    date = models.DateField(default=date.today)
    profit = MoneyField(max_digits=12, decimal_places=2)
    adjusted_profit = MoneyField(max_digits=12, decimal_places=2)
    capital = MoneyField(max_digits=12, decimal_places=2)
    liability = MoneyField(max_digits=12, decimal_places=2)
    loan_liability = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    fixed_asset = MoneyField(max_digits=12, decimal_places=2)
    current_asset = MoneyField(max_digits=12, decimal_places=2)
    investment = MoneyField(max_digits=12, decimal_places=2)
    suspense = MoneyField(max_digits=12, decimal_places=2)
    difference = MoneyField(max_digits=12, decimal_places=2)
    sundry_debtor = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))

    def __str__(self) -> str:
        return f'BS-{self.date}'

    def get_absolute_url(self):
        return reverse('trade-bs-detail', kwargs={'pk': self.pk})
    
    def growth_ratio(self):
        return round(100*self.profit/self.capital, 2)

    def debt_to_equity_ratio(self):
        return round(100*self.liability/self.capital, 2)

    def current_ratio(self):
        if self.liability > Money(0, 'NGN'):
            return round(self.current_asset/self.liability, 3)
        return None
    
    def quick_ratio(self):
        if self.liability > Money(0, 'NGN'):
            obj = TradeDaily.objects.filter(date=self.date)
            inventory = obj.get().closing_value if obj.exists() else Money(0, 'NGN')
            return round((self.current_asset - self.sundry_debtor - inventory)/self.liability, 3)
        return None



class BankAccount(models.Model):
    account_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50)
    account_number = models.CharField(max_length=12)
    bank = models.CharField(max_length=30)
    lien_amount = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    account_group = models.CharField(max_length=20, default='Business')
    status = models.BooleanField(default=True)


    def __str__(self) -> str:
        return self.nickname
    
    def get_absolute_url(self):
        return reverse('bank-balance-create')


class BankBalance(models.Model):
    bank = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    bank_balance = MoneyField(max_digits=12, decimal_places=2)
    account_package_balance = MoneyField(max_digits=12, decimal_places=2)
    
    class Meta:
        unique_together = (("bank", "date"),)

    def __str__(self) -> str:
        return f'{self.bank.nickname}-{self.date}'
    
    def get_absolute_url(self):
        return reverse('bank-balance-detail', kwargs={'pk': self.pk})

    def delta(self):
        return self.bank_balance - self.account_package_balance