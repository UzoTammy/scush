import uuid

from django.shortcuts import reverse
from django.db import models
from django.utils import timezone
import datetime
from ozone import mytools


def _invite_expiry():
    return timezone.now() + datetime.timedelta(days=3)


class ApplicationInvite(models.Model):
    email      = models.EmailField()
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_invite_expiry)
    used       = models.BooleanField(default=False)

    def __str__(self):
        return f'Invite → {self.email}'

    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at


class ApplicantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

class ThisYearApplicantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(apply_date__year=datetime.date.today().year)

class EmployedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(state='Employed')

class PendingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(state='Applied')

class RejectedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(state='Rejected')

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
    state = models.CharField(max_length=10, default='Applied',
                             choices=[('Applied', 'Applied'), ('Interview', 'Interview'),
                                      ('Guarantor', 'Guarantor'), ('Employed', 'Employed'),
                                      ('Rejected', 'Rejected'), ('Resigned', 'Resigned'),
                                      ('Sacked', 'Sacked'), ('Re-Engaged', 'Re-Engaged')])
    resignation_reason = models.TextField(blank=True, null=True)
    
    objects = ApplicantManager()
    this_year = ThisYearApplicantManager()
    employed = EmployedManager()
    pending = PendingManager()
    rejected = RejectedManager()
    
    
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


class Interview(models.Model):
    PASS = 'Pass'
    FAIL = 'Fail'
    RESULT_CHOICES = [(PASS, 'Pass'), (FAIL, 'Fail')]

    applicant   = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name='interview')
    interviewer = models.ForeignKey('staff.Employee', on_delete=models.SET_NULL,
                                   null=True, related_name='interviews_conducted')
    result      = models.CharField(max_length=4, choices=RESULT_CHOICES)
    date        = models.DateField(default=timezone.now)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.applicant} — {self.result}'


class GuarantorDocument(models.Model):
    applicant   = models.OneToOneField(Applicant, on_delete=models.CASCADE, related_name='guarantor_doc')
    document    = models.FileField(upload_to='guarantor_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                   null=True, related_name='guarantor_uploads')

    # Re-upload (the guarantor declined / document needs replacing) — gated by approval
    reupload_requested    = models.BooleanField(default=False)
    reupload_reason       = models.TextField(blank=True, null=True)
    reupload_requested_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                              null=True, blank=True, related_name='guarantor_reupload_requests')
    reupload_requested_at = models.DateTimeField(null=True, blank=True)
    reupload_approved     = models.BooleanField(default=False)
    reupload_approved_by  = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                              null=True, blank=True, related_name='guarantor_reupload_approvals')

    def __str__(self):
        return f'Guarantor Doc — {self.applicant}'

    