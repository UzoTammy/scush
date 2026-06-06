import datetime
import uuid

from django.db import models
from django.utils import timezone


def _default_link_expiry():
    return timezone.now() + datetime.timedelta(days=14)


class JobPosting(models.Model):
    STATUS_OPEN   = 'Open'
    STATUS_CLOSED = 'Closed'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_CLOSED, 'Closed')]

    title         = models.CharField(max_length=150)
    department    = models.CharField(max_length=100)
    location      = models.CharField(max_length=100, default='Lagos, Nigeria')
    description   = models.TextField(help_text='Roles and responsibilities')
    requirements  = models.TextField(help_text='Qualifications and experience required')
    deadline      = models.DateField()
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    contact_email = models.EmailField(default='contact@ozonefl.com')
    posted_date   = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['-posted_date']
        verbose_name = 'Job Posting'
        verbose_name_plural = 'Job Postings'

    def __str__(self):
        return f'{self.title} ({self.department})'

    def is_open(self):
        return self.status == self.STATUS_OPEN and self.deadline >= timezone.now().date()


class JobApplication(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_SUBMITTED = 'submitted'
    STATUS_INTERVIEW = 'interview'
    STATUS_ACCEPTED  = 'accepted'
    STATUS_EMPLOYED  = 'employed'
    STATUS_REJECTED  = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_SUBMITTED, 'Form Submitted'),
        (STATUS_INTERVIEW, 'Interview Granted'),
        (STATUS_ACCEPTED,  'Accepted – Awaiting Guarantor'),
        (STATUS_EMPLOYED,  'Employed'),
        (STATUS_REJECTED,  'Rejected'),
    ]

    job             = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    token           = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Set by HR when creating the record
    applicant_name  = models.CharField(max_length=200)
    applicant_email = models.EmailField()

    # Filled by applicant via token link
    phone           = models.CharField(max_length=20, blank=True)
    date_of_birth   = models.DateField(null=True, blank=True)
    address         = models.TextField(blank=True)
    education       = models.TextField(blank=True, help_text='Highest qualification and institution')
    experience      = models.TextField(blank=True, help_text='Relevant work experience')
    cover_letter    = models.TextField(blank=True)

    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at      = models.DateTimeField(auto_now_add=True)
    submitted_at    = models.DateTimeField(null=True, blank=True)
    link_expires_at = models.DateTimeField(default=_default_link_expiry)
    hr_notes        = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job Application'
        verbose_name_plural = 'Job Applications'

    def __str__(self):
        return f'{self.applicant_name} → {self.job.title}'

    def has_guarantor(self):
        return hasattr(self, 'guarantor')

    def is_link_expired(self):
        return timezone.now() > self.link_expires_at

    def extend_link(self, days=14):
        self.link_expires_at = timezone.now() + datetime.timedelta(days=days)
        self.save(update_fields=['link_expires_at'])


class Guarantor(models.Model):
    ID_CHOICES = [
        ('national_id', 'National ID Card'),
        ('passport',    'International Passport'),
        ('drivers',     "Driver's Licence"),
        ('voters',      "Voter's Card"),
    ]

    application    = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name='guarantor')
    token          = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Filled by guarantor via token link
    full_name      = models.CharField(max_length=200, blank=True)
    address        = models.TextField(blank=True)
    occupation     = models.CharField(max_length=150, blank=True)
    employer       = models.CharField(max_length=150, blank=True)
    phone          = models.CharField(max_length=20, blank=True)
    email          = models.EmailField(blank=True)
    relationship   = models.CharField(max_length=100, blank=True, help_text='Relationship to applicant')
    id_type        = models.CharField(max_length=20, choices=ID_CHOICES, blank=True)
    id_number      = models.CharField(max_length=60, blank=True)
    agreed          = models.BooleanField(default=False)
    submitted_at    = models.DateTimeField(null=True, blank=True)
    link_expires_at = models.DateTimeField(default=_default_link_expiry)

    # HR decision: None = pending, True = approved, False = rejected
    approved        = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = 'Guarantor'
        verbose_name_plural = 'Guarantors'

    def __str__(self):
        return f'Guarantor for {self.application.applicant_name}'

    def is_submitted(self):
        return self.submitted_at is not None

    def is_link_expired(self):
        return timezone.now() > self.link_expires_at

    def extend_link(self, days=14):
        self.link_expires_at = timezone.now() + datetime.timedelta(days=days)
        self.save(update_fields=['link_expires_at'])
