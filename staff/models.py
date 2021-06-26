from django.db import models
from djmoney.models.fields import MoneyField
from djmoney.models.validators import MaxMoneyValidator, MinMoneyValidator
from django.utils import timezone
from django.urls import reverse
from apply.models import Applicant
from djmoney.money import Money
import datetime


class ActiveEmployeeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=True)


class Employee(models.Model):

    DUTY_CHOICE = [('Nil', 'Nil'),
                   ('Leave', 'Leave'),
                   ('Training', 'Training'),
                   ('Suspension', 'Suspension'),
                   ('Terminated', 'Terminated')
                   ]
    BANKS = [('UBA', 'UBA'),
             ('GTB', "GTB"),
             ('FCMB', "FCMB"),
             ('First Bank', 'First Bank'),
             ('Union Bank', 'Union Bank'), ('Access', 'Access'), ('Sterling', 'Sterling'), ('Polaris', 'Polaris'),
             ('Heritage', 'Heritage'), ('Stanbic', 'Stanbic'), ('Fidelity', 'Fidelity'), ('Ecobank', 'Ecobank'),
             ('Zenith', 'Zenith'), ('Unity', 'Unity'), ('Wema', 'Wema')
             ]
    POSITIONS = [("Cashier", "Cashier"),
                 ("Store-Keeper", "Store-Keeper"),
                 ("Stock-Keeper", "Stock-Keeper"),
                 ("Accounts-Clerk", "Accounts-Clerk"),
                 ("Sales-Clerk", "Sales-Clerk"),
                 ("Accountant", "Accountant"),
                 ("HRM", "HRM"),
                 ("SCM", "SCM"),
                 ("GSM", "GSM"),
                 ("MD", "Managing Director"),
                 ("Analyst", "Analyst"),
                 ("Sales Rep", "Sales Rep"),
                 ("Marketing Manager", "Marketing Manager"),
                 ('Driver', 'Driver')
                 ]
    BRANCHES = [("HQ", "HQ"), ("FG", "FG"), ("Genesis", "Genesis"),
                ('Stardom', 'Stardom'), ('Vino', 'Vino'), ('Island', 'Island'),
                ('Badagry', 'Badagry')]
    DEPARTMENTS = [("Sales", "Sales"),
                   ('Marketing', 'Marketing'),
                   ('Admin', 'Admin'),
                   ('Accounts', 'Accounts'),
                   ("HR", "HR")]

    size = lambda BANKS: BANKS[1]
    BANKS.sort(key=size)

    staff = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='staff_pics', blank=True)
    date_employed = models.DateField(default=timezone.now,
                                     help_text='<em style=color:red;>YYYY-MM-DD</em>')
    official_email = models.EmailField(max_length=50, blank=True, null=True,
                                       help_text='<em style=color:red;>firstname.lastname@ozonefl.com</em>')
    official_mobile = models.CharField(max_length=11, blank=True, null=True)
    is_management = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    position = models.CharField(max_length=30, null=True, blank=True,
                                choices=POSITIONS)
    department = models.CharField(max_length=30, null=True, blank=True,
                                  choices=DEPARTMENTS)
    branch = models.CharField(max_length=30, null=True, blank=True,
                              choices=BRANCHES)
    banker = models.CharField(max_length=20, choices=BANKS, default='UBA')
    account_number = models.CharField(max_length=10)
    basic_salary = MoneyField(max_digits=8,
                              decimal_places=2,
                              default_currency='NGN',
                              validators=[
                                  MinMoneyValidator(1000),
                                  MaxMoneyValidator(200000),
                              ])
    allowance = MoneyField(max_digits=8,
                           decimal_places=2,
                           default_currency='NGN',
                           validators=[
                               MinMoneyValidator(0),
                               MaxMoneyValidator(300000),
                           ])
    tax_amount = MoneyField(max_digits=6,
                            decimal_places=2,
                            default_currency='NGN',
                            validators=[
                               MinMoneyValidator(0),
                               MaxMoneyValidator(5000),
                           ])
    status = models.BooleanField(default=True,
                                 choices=[(True, 'Active'),
                                          (False, 'Terminated')])
    balance = MoneyField(max_digits=10,
                         decimal_places=2,
                         default_currency='NGN',
                         default=Money(0, 'NGN'),
                         )

    objects = models.Manager()
    active = ActiveEmployeeManager()

    def __str__(self):
        return f'{self.staff}'

    def get_absolute_url(self):
        return reverse('employee-detail', kwargs={'pk': self.pk})

    def salary(self):
        return self.basic_salary + self.allowance

    def fullname(self):
        return f"{self.staff.first_name} {self.staff.second_name} {self.staff.last_name}"

    def gross_pay(self):
        return self.salary() - self.tax_amount

    def netpay(self):
        return self.gross_pay()-self.debit()+self.credit()


class CreditNote(models.Model):
    today = datetime.date.today()
    name = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.CharField(max_length=7, default=f'{today.year}-{str(today.month).zfill(2)}')
    credit_date = models.DateField(default=timezone.now)
    remark = models.CharField(max_length=50)
    value = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN')
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}-{self.period}"


class DebitNote(models.Model):
    today = datetime.date.today()
    name = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.CharField(max_length=7, default=f'{today.year}-{str(today.month).zfill(2)}')
    debit_date = models.DateField(default=timezone.now)
    remark = models.CharField(max_length=50, blank=True, null=True)
    value = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN')
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}-{self.period}"


class StaffStatement(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_posted = models.DateField(default=timezone.now)
    note = models.CharField(max_length=100)
    opening_balance = MoneyField(max_digits=8, decimal_places=2,
                                 default_currency='NGN')
    credit_note = models.ForeignKey(CreditNote, blank=True, null=True, on_delete=models.CASCADE)
    debit_note = models.ForeignKey(DebitNote, blank=True, null=True, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff}-{str(self.id).zfill(3)}"

    def closing_balance(self):
        if self.credit_note is None:
            credit = Money(0, 'NGN')
        else:
            credit = ''
        if self.debit_note is None:
            debit = Money(0, 'NGN')
        return self.opening_balance + credit - debit


class Payroll(models.Model):
    period = models.CharField(max_length=7)
    date_paid = models.DateField(default=timezone.now)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    credit_amount = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    debit_amount = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    net_pay = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    deduction = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    outstanding = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    status = models.BooleanField(default=False)
    # status: True means paid and False means not paid

    def __str__(self):
        return f"{self.staff.fullname()}:{self.period}"
