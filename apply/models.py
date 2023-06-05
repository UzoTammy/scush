from django.shortcuts import reverse
from django.db import models
from django.utils import timezone
import datetime
from ozone import mytools

class ApplicantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

class ThisYearApplicantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(apply_date__year=datetime.date.today().year)

class EmployedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=True)

class PendingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=None)

class RejectedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=False)

class Applicant(models.Model):
    first_name = models.CharField(max_length=30)
    second_name = models.CharField(max_length=30,
                                   blank=True, null=True)
    last_name = models.CharField(max_length=30)
    birth_date = models.DateField()
    gender = models.CharField(max_length=10,
                              choices=[('FEMALE', 'Female'),
                                       ('MALE', 'Male')],
                              default='MALE')
    marital_status = models.CharField(max_length=10,
                                      choices=[('MARRIED', 'Married'),
                                               ('SINGLE', 'Single')],
                                      default='SINGLE')
    qualification = models.CharField(max_length=20, choices=[
        ('NONE', 'None'), ('PRIMARY', 'Primary'), ('SECONDARY', 'Secondary'),
        ('ND/NCE', 'ND or NCE'), ('HND/HCE', 'HND or HCE'),
        ('BACHELOR', 'First Degree'), ('MASTERS', 'Masters'),
    ], default='NONE')

    course = models.CharField(max_length=50, blank=True, null=True)
    mobile = models.CharField(max_length=13)
    email = models.EmailField(blank=True, null=True)
    apply_date = models.DateField(default=timezone.now)
    modified_date = models.DateTimeField(default=timezone.now)
    address = models.CharField(max_length=100)
    status = models.BooleanField(choices=[(True, 'Employed'), (None, 'Pending'),
                                          (False, 'Rejected')],
                                 null=True, blank=True)
    
    this_year = ThisYearApplicantManager()
    employed = EmployedManager()
    pending = PendingManager()
    rejected = RejectedManager()
    objects = ApplicantManager()
    

    
    def __str__(self):
        return f'{self.last_name}, {self.first_name} {self.second_name}'

    def get_absolute_url(self):
        return reverse('apply-detail', kwargs={'pk': self.pk})

    
    def get_age(self):
        today = datetime.date.today()
        birthday = self.birth_date.replace(today.year)
        if birthday > today:
            return today.year - self.birth_date.year - 1
        return today.year - self.birth_date.year
    
    def get_age_string(self):
        date_string = self.birth_date.strftime('%d-%m-%Y')
        years_str = mytools.DatePeriod(date_string).year_month_week_day()
        return years_str

    def get_apply_age_string(self):
        date_string = self.apply_date.strftime('%d-%m-%Y')
        years_str = mytools.DatePeriod(date_string).year_month_week_day()
        return years_str


