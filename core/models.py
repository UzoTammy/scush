from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError

class JsonDataset(models.Model):
    name = models.CharField(max_length=50)
    dataset = models.JSONField(default=dict, verbose_name="Json Format")

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse('json-detail', kwargs={'pk': self.pk})


class Setting(models.Model):
    TYPE_TEXT   = 'text'
    TYPE_NUMBER = 'number'
    TYPE_DATE   = 'date'
    TYPE_LIST   = 'list'
    VALUE_TYPE_CHOICES = [
        (TYPE_TEXT,   'Text'),
        (TYPE_NUMBER, 'Number'),
        (TYPE_DATE,   'Date'),
        (TYPE_LIST,   'List'),
    ]

    key        = models.CharField(max_length=100, unique=True)
    label      = models.CharField(max_length=100)
    category   = models.CharField(max_length=50)
    value_type = models.CharField(max_length=10, choices=VALUE_TYPE_CHOICES, default=TYPE_TEXT)
    text_value = models.TextField(blank=True, default='')
    list_value = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['category', 'label']

    def __str__(self):
        return f'{self.category} / {self.label}'

    @classmethod
    def get_list(cls, key, default=None):
        try:
            return cls.objects.get(key=key).list_value
        except cls.DoesNotExist:
            return default if default is not None else []

    @classmethod
    def get_value(cls, key, default=''):
        try:
            return cls.objects.get(key=key).text_value
        except cls.DoesNotExist:
            return default


class CompanyProfile(models.Model):
    """A single record holding company-level information.

    Fields are grouped into two categories:
      - Static: legal/registration details that rarely change.
      - Dynamic: operational details that are kept current day-to-day.
    """

    # ── Static (legal / registration) ──────────────────────────────
    legal_name = models.CharField(max_length=150)
    rc_number = models.CharField('RC Number', max_length=30, blank=True)
    tin = models.CharField('TIN', max_length=30, blank=True)
    date_incorporated = models.DateField(null=True, blank=True)
    registered_address = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company', blank=True, null=True)

    # ── Dynamic (operational, kept current) ────────────────────────
    tagline = models.CharField(max_length=150, blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    head_office_address = models.TextField(blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField('X (Twitter)', blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.legal_name

    def clean(self):
        if not self.pk and CompanyProfile.objects.exists():
            raise ValidationError('A Company Profile already exists; only one is allowed.')

    @classmethod
    def load(cls):
        """Return the single CompanyProfile instance, creating it if absent."""
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'legal_name': ''})
        return obj


