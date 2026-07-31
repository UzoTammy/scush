from django.contrib import admin
from .models import JsonDataset, CompanyProfile

# Register your models here.
admin.site.register(JsonDataset)
admin.site.register(CompanyProfile)