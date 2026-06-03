from decimal import Decimal
from django.conf import settings
from django.db import models
from djmoney.models.fields import MoneyField, Money
from django.urls.base import reverse
from datetime import date


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

    locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='locked_periods',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

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
    account_package_balance = MoneyField(max_digits=12, decimal_places=2) #busy balance
    
    class Meta:
        unique_together = (("bank", "date"),)

    def __str__(self) -> str:
        return f'{self.bank.nickname}-{self.date}'
    
    def get_absolute_url(self):
        return reverse('bank-balance-detail', kwargs={'pk': self.pk})

    def delta(self):
        return self.bank_balance - self.account_package_balance
    

class Creditor(models.Model):
    account = models.CharField(max_length=50)
    date = models.DateField(default=date.today)
    amount = MoneyField(max_digits=12, decimal_places=2)
    ledger = models.CharField(max_length=2, default='CR', choices=[('CR', 'Cr'), ('DR', 'Dr')])
    account_type = models.CharField(max_length=10, default='Ext', choices=[('Ext', 'External'), ('Int', 'Internal')])
    status = models.BooleanField(default=True)

    class Meta:
        unique_together = (("account", "date"),)


class CashProjection(models.Model):
    FLOW_OUT = 'OUT'
    FLOW_IN  = 'IN'
    FLOW_CHOICES = [('IN', 'Inflow'), ('OUT', 'Outflow')]

    CATEGORY_CHOICES = [
        ('salary',   'Salary / Payroll'),
        ('rent',     'Rent'),
        ('loan',     'Loan Repayment'),
        ('tax',      'Tax'),
        ('supplier', 'Supplier Payment'),
        ('utility',  'Utility'),
        ('other',    'Other'),
    ]

    description   = models.CharField(max_length=100)
    amount        = MoneyField(max_digits=12, decimal_places=2)
    expected_date = models.DateField()
    flow_type     = models.CharField(max_length=3, choices=FLOW_CHOICES, default=FLOW_OUT)
    category      = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    is_recurring  = models.BooleanField(default=False, help_text='Tick if this repeats monthly')
    notes         = models.TextField(blank=True)

    class Meta:
        ordering = ['expected_date']

    def __str__(self):
        sign = '+' if self.flow_type == self.FLOW_IN else '-'
        return f'{self.expected_date} {sign}{self.amount} — {self.description}'

    def get_absolute_url(self):
        return reverse('cash-projection-list')

    def signed_amount(self):
        return self.amount if self.flow_type == self.FLOW_IN else -self.amount


class TradeAdjustmentRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    model_name = models.CharField(max_length=50)
    record_id = models.PositiveIntegerField()
    record_str = models.CharField(max_length=100)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='adjustment_requests',
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    proposed_changes = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_adjustments',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Adjustment Request'
        verbose_name_plural = 'Adjustment Requests'

    def __str__(self):
        return f'{self.model_name} #{self.record_id} — {self.requester} ({self.status})'


class TradeAuditLog(models.Model):
    model_name = models.CharField(max_length=50)
    record_id = models.PositiveIntegerField()
    record_str = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='trade_audit_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f'{self.model_name} #{self.record_id} — {self.user} @ {self.timestamp:%Y-%m-%d %H:%M}'
