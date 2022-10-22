import calendar
import datetime
from django.db import models
from django.utils import timezone
from django.urls import reverse
from djmoney.money import Money
from django.contrib.auth.models import User
from djmoney.models.fields import MoneyField
from djmoney.models.validators import MaxMoneyValidator, MinMoneyValidator
from ozone import mytools
from apply.models import Applicant


class ActiveEmployeeManager(models.Manager):
    def get_queryset(self):
        """Either True for active or false for Terminated Employee"""
        return super().get_queryset().filter(status=True)


class Employee(models.Model):

    staff = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='staff_pics', blank=True)
    date_employed = models.DateField(default=timezone.now,
                                     help_text='<em style=color:red;>YYYY-MM-DD</em>')
    official_email = models.EmailField(max_length=50, blank=True, null=True,
                                       help_text='<em style=color:red;>firstname.lastname@ozonefl.com</em>')
    official_mobile = models.CharField(max_length=11, blank=True, null=True)
    is_management = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    position = models.CharField(max_length=30, null=True, blank=True)
    department = models.CharField(max_length=30, null=True, blank=True)
    branch = models.CharField(max_length=30, null=True, blank=True)
    banker = models.CharField(max_length=20)
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

# Gratuity
class EmployeeBalance(models.Model):
    today = datetime.date.today()
    period = models.CharField(max_length=7, default=f'{today.year}-{str(today.month).zfill(2)}')
    title = models.CharField(max_length=30, default=f'0821-Sales')
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    value = MoneyField(max_digits=10, decimal_places=2, default=Money(0, 'NGN'))
    value_type = models.CharField(max_length=2, default='Cr')
    description = models.CharField(max_length=50)
    


    def __str__(self):
        return f'{self.staff}-{self.period}'
    
    def get_absolute_url(self):
        return reverse('employeebalance-detail', kwargs={'pk': self.pk})

class SalaryChange(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    previous_value = MoneyField(max_digits=8,
                                decimal_places=2,
                                default=Money(0, 'NGN'))
    value = MoneyField(max_digits=8, decimal_places=2)
    remark = models.CharField(max_length=100)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.staff.fullname()}-{self.id}"

class Permit(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    starting_from = models.DateTimeField(default=timezone.now)
    ending_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=150)

    def __str__(self):
        return f"""{self.staff.fullname()}-{self.id}"""

    def get_absolute_url(self):
        return reverse('request-permission-list')

    def duration(self):
        if self.starting_from.date() == self.ending_at.date():
            delta = (self.ending_at - self.starting_from).total_seconds()
            # 1hr = 3600 seconds
            hours = int(divmod(delta, 3600)[0])
            return f'{hours}H'
        else:
            days = len(mytools.DateRange(self.starting_from.date(), self.ending_at.date()).exclude_weekday(calendar.SUNDAY))
            return f'{days - 1}D'

class Reassign(models.Model):
    
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reassign_type = models.CharField(max_length=10, default='Temporal',
                                     choices=[('T', 'Temporal'),
                                              ('A', 'Acting'),
                                              ('C', 'Confirmed')]
                                     )
    from_position = models.CharField(max_length=30, null=True, blank=True)
    to_position = models.CharField(max_length=30, null=True, blank=True)
    from_branch = models.CharField(max_length=30, null=True, blank=True)
    to_branch = models.CharField(max_length=30, null=True, blank=True)
    start_date = models.DateField(default=timezone.now)
    duration = models.SmallIntegerField(default=0)
    remark = models.CharField(max_length=100)

    def __str__(self):
        return self.staff.fullname()

class Suspend(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    resumption_date = models.DateField(default=timezone.now)
    reason = models.CharField(max_length=100)
    penalty = MoneyField(max_digits=7, decimal_places=2)

    def __str__(self):
        return f"""{self.staff.fullname()}-{self.id}"""

class Terminate(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    termination_type = models.CharField(max_length=6, default='Resign',
                                        choices=[('Resign', 'Resign'),
                                                 ('Sack', 'Sack')]
                                        )
    remark = models.CharField(max_length=100)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.staff.fullname()

class Welfare(models.Model):
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=150)
    amount = models.FloatField(default=0.0)

# Create User will be seen in users model

class Payroll(models.Model):
    period = models.CharField(max_length=7)
    date_paid = models.DateField(default=timezone.now)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    credit_amount = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    debit_amount = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    net_pay = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    deduction = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    outstanding = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    salary = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    tax = MoneyField(max_digits=8, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    status = models.BooleanField(default=False)
    """status: True means paid and False means not paid"""
    balance = MoneyField(max_digits=9, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))

    class Meta:
        verbose_name_plural = 'Payroll'

    def __str__(self):
        return f"{self.staff.fullname()}-{self.period}"

    def period_month(self):
        month = self.period.split('-')[1]
        year = self.period.split('-')[0]
        period_month = mytools.Period.full_months[month]
        return f'{period_month}, {year}'

    def gross_pay(self):
        return self.salary - self.tax

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

class RequestPermission(models.Model):
    request_by = models.ForeignKey(User, on_delete=models.CASCADE)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now, blank=True)
    reason = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    resume_date = models.DateTimeField()
    status = models.BooleanField(default=None, null=True, blank=True) #true: approved, #false: disapproved, #none: pending

    
    def __str__(self):
        return f'{self.staff} permission request'

    def get_absolute_url(self):
        return reverse('home')


    def duration(self):
        if self.start_date.date() == self.resume_date.date():
            delta = (self.resume_date - self.start_date).total_seconds()
            # 1hr = 3600 seconds
            hours = int(divmod(delta, 3600)[0])
            return f'{hours}H'
        else:
            days = len(mytools.DateRange(self.start_date.date(), self.resume_date.date()).exclude_weekday(calendar.SUNDAY))
            return f'{days - 1}D'


