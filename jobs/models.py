from django.db import models
from django.utils import timezone


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
