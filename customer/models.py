from django.db import models
from django.urls.base import reverse_lazy
from django.utils import timezone
from django.urls import reverse
from djmoney.models.fields import Money, MoneyField
import json
import os
from django.conf import settings


json_path = os.path.join(settings.BASE_DIR, "customer/static/customer/customer.json")

with open(json_path, 'r') as rf:
    content = json.load(rf)

cluster_choices = list()
for i in content['cluster']:
    cluster_choices.append((i.upper(), i))

category_choices = list()
for i in content['category']:
    category_choices.append((i.upper(), i))


class CustomerProfile(models.Model):
    business_name = models.CharField(max_length=100)
    business_owner = models.CharField(max_length=50, null=True, blank=True)
    cluster = models.CharField(max_length=30,
                               choices=cluster_choices)
    address = models.CharField(max_length=100)
    mobile = models.CharField(max_length=11)
    email = models.EmailField(blank=True, null=True, help_text="<span class='text-danger'>not compulsory</span>")

    type = models.CharField(max_length=10, default='NA', choices=[('NA', 'Non-Alcoholic'), 
    ('A', 'Alcoholic'), ('U', 'Unknown')])
    section = models.CharField(max_length=30, default='C & P')
    sales = MoneyField(max_digits=12, default_currency='NGN', decimal_places=2, default=Money(0, 'NGN'))
    freq = models.IntegerField(default=0)
    category = models.CharField(max_length=30,
                                choices=category_choices)
    region = models.CharField(max_length=30,
                              choices=[('LAGOS', 'Lagos')],
                              default='LAGOS')
    date_created = models.DateTimeField(default=timezone.now)
    date_modified = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})


