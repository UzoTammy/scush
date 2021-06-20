from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
import json
import os


json_path = os.path.join("./customer/static/customer", "customer.json")

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
    category = models.CharField(max_length=30,
                                choices=category_choices)
    address = models.CharField(max_length=100)
    mobile = models.CharField(max_length=11)
    email = models.EmailField(blank=True, null=True, help_text="<span class='text-danger'>not compulsory</span>")
    date_created = models.DateTimeField(default=timezone.now)
    date_modified = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    region = models.CharField(max_length=30,
                              choices=[('LAGOS', 'Lagos')],
                              default='LAGOS')
    # active = models.BooleanField(default=True)
    # manager = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})
