from django.contrib import admin
from .models import Stores, Renewal, BankAccount

admin.site.register(Stores)
admin.site.register(Renewal)
admin.site.register(BankAccount)