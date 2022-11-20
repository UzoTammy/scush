from django.db import models
from django.urls.base import reverse_lazy
from django.utils import timezone
from django.urls import reverse
from djmoney.models.fields import Money, MoneyField
import json
import os
from django.conf import settings


json_path = os.path.join(settings.BASE_DIR, "core/static/customer/customer.json")

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
    address = models.CharField(max_length=120)
    cluster = models.CharField(max_length=3,
                               choices=[('TRF', 'Trade Fair'), ('FES', 'Festac'), ('OMO', 'Omonile'),
                                ('OKO', 'Okoko'), ('BAD', 'Badagry'), ('SAT', 'Satellite'),
                                ('BAR', 'Barracks'), ('LIS', 'Lagos Island'), ('NC', 'No Cluster')],
                            default='TRF')
    region = models.CharField(max_length=3,
                              choices=[('LOS', 'Lagos'), ('DSP', 'Diaspora'), ('OLS', 'Outside Lagos')],
                              default='LOS')
    mobile = models.CharField(max_length=14)
    second_mobile = models.CharField(max_length=14, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, help_text="<span class='text-danger'>not compulsory</span>")
    classification = models.CharField(max_length=3, choices=[('RTN', 'Returnable'), ('OWP', '1-Way Pack'), 
        ('WIN', 'Wine'), ('ROW', 'Returnable+1-Way'), ('OWW', '1-Way+Wine'), ('ALL', 'All'),
        ('RTW', 'Returnable+Wine')],
    default='OWP'
    )
    contact_person = models.CharField(max_length=50, blank=True, null=True, help_text="firstname, mobile number")
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})
