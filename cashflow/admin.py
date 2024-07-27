from django.contrib import admin
from .models import CashCollect, CashDepot, Disburse, Withdrawal

# Register your models here.
admin.site.register(CashCollect)
admin.site.register(CashDepot)
admin.site.register(Disburse)
admin.site.register(Withdrawal)