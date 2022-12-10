from django.contrib import admin
from .models import Profile as CustomerProfile, CustomerCredit

# Register your models here.
admin.site.register(CustomerProfile)
admin.site.register(CustomerCredit)