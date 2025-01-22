from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import User

from djmoney.models.fields import MoneyField
from djmoney.money import Money

# Create your models here.
class BankAccount(models.Model):
    account_number = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=30)
    lien_value = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    opening_balance = MoneyField(max_digits=12, decimal_places=2)
    current_balance = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    opening_balance_date = models.DateField()
    category = models.CharField(max_length=25) # Business & Admin
    status = models.BooleanField(default=True) # active
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.short_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.short_name}-{self.account_number}'
    
    def deposit(self, amount, description, timestamp, user):

        self.current_balance += amount
        self.save()

        BankTransaction.objects.create(
            bank=self, transaction_type='CR', amount=amount, 
            description=description, timestamp=timestamp,
            initiated_by=user, approved_by=user
        )

    def withdraw(self, amount, description, timestamp, user):
        self.current_balance -= amount
        self.save()

        BankTransaction.objects.create(
            bank=self, transaction_type='DR', amount=amount, 
            description=description, timestamp=timestamp,
            initiated_by=user, approved_by=user
        )


class CashCenter(models.Model):
    name = models.CharField(max_length=100)
    opening_balance = MoneyField(max_digits=12, decimal_places=2)
    opening_balance_date = models.DateField()
    current_balance = MoneyField(max_digits=12, decimal_places=2, default=Money(0, 'NGN'))
    status = models.BooleanField(default=True) # active
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.name}'
    
    def deposit(self, amount, description, timestamp, user):

        self.current_balance += amount
        self.save()

        CashTransaction.objects.create(
            cash_center=self, transaction_type='CR', amount=amount, 
            description=description, timestamp=timestamp,
            initiated_by=user
        )

    def withdraw(self, amount, description, timestamp, user):
        self.current_balance -= amount
        self.save()

        CashTransaction.objects.create(
            cash_center=self, transaction_type='DR', amount=amount, 
            description=description, timestamp=timestamp,
            initiated_by=user
        )


class BankTransaction(models.Model):
    TRANSACTION_TYPES = (
        ("CR", "Deposit"),
        ("DR", "Withdraw"),
    )

    bank = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=12, decimal_places=2)  # Can be positive (Deposit) or negative (Withdrawal)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals')

    def __str__(self):
        return f"{self.bank.account_number} - {self.transaction_type}: {self.amount} @ {self.timestamp}"
    
    # def get_balance(self, period=None):
    #     if period is None:
    #         balance = self.bank.opening_balance

    #     if self.transaction_type == 'DR':
    #         opening_balance =- self.amount
    #     opening_balance += self.amount
    #     return balance
    
class CashTransaction(models.Model):
    TRANSACTION_TYPES = (
        ("CR", "Deposit"),
        ("DR", "Withdraw"),
    )

    cash_center = models.ForeignKey(CashCenter, on_delete=models.CASCADE, related_name='cash_transactions')
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=12, decimal_places=2)  # Can be positive (Deposit) or negative (Withdrawal)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals')

    def __str__(self):
        return f"{self.name} - {self.transaction_type}: {self.amount} @ {self.timestamp}"




## Will be discarded


class CashDepot(models.Model):
    # affected by cash collection and deposit
    date = models.DateField()
    balance = MoneyField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f'Cash {self.balance}'

class CashCollect(models.Model):
    # gathering cash into cash depot
    source = models.CharField(max_length=30)
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = models.DateField(default=timezone.now)
    collector =  models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.source}-{self.post_date}'

class CashDeposit(models.Model):
    # taking cash from cash depot into bank account
    bank = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = models.DateField(default=timezone.now)
    depositor =  models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.bank.short_name}-{self.post_date}'
    

class Transaction(models.Model):
    data = models.JSONField(default=list)  # Stores a list of dictionaries

class Disburse(models.Model):
    requested_by = models.CharField(max_length=30)
    amount = MoneyField(max_digits=8, decimal_places=2)
    purpose = models.CharField(max_length=200)
    has_detail = models.BooleanField(default=False)
    request_date = models.DateField(default=timezone.now)

    def __str__(self) -> str:
        return f'Disburse {self.requested_by}-{self.request_date}'

class Withdrawal(models.Model):
    # taking funds from bank to Party
    bank = models.ForeignKey(BankAccount, on_delete=models.CASCADE, blank=True, null=True)
    party = models.CharField(max_length=30)
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = models.DateField(default=timezone.now)
    requested_by =  models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    decided_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decisions', blank=True, null=True)
    particulars = models.CharField(max_length=20, blank=True, null=True)
    stage = models.SmallIntegerField(default=0)
    # remark = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return f'{self.party}: {self.amount}'

class InterbankTransfer(models.Model):
    # taking funds from bank to bank internally
    sender_bank = models.ForeignKey(BankAccount,related_name='sent_transfer', on_delete=models.CASCADE)
    receiver_bank = models.ForeignKey(BankAccount, related_name='received_transfer', on_delete=models.CASCADE)
    amount = MoneyField(max_digits=12, decimal_places=2)
    transfer_date = models.DateField(auto_now=True)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.sender_bank.short_name} to {self.receiver_bank.short_name}: {self.amount}'

class BankTransact(models.Model):
    bank = models.ForeignKey(BankAccount, on_delete=models.CASCADE) 
    post_date = models.DateField()
    amount = MoneyField(max_digits=12, decimal_places=2)
    processed_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class BankTransfer(BankTransact):
    
    def __str__(self) -> str:
        return f'Transfer {self.post_date} {self.amount}'

class BankCharges(BankTransact):
    
    def __str__(self) -> str:
        return f'Charges {self.post_date} {self.amount}'

    