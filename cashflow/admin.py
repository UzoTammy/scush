from django.contrib import admin
from .models import (CashCollect, CashDepot, Disburse, Withdrawal, CashTransaction,
                     CashDeposit, BankAccount, Transaction, BankTransaction, CashCenter)

# Register your models here.
admin.site.register(CashCollect)
admin.site.register(CashDepot)
admin.site.register(Disburse)
admin.site.register(Withdrawal)
admin.site.register(CashDeposit)
admin.site.register(BankAccount)
admin.site.register(CashCenter)
admin.site.register(Transaction)
admin.site.register(BankTransaction)
admin.site.register(CashTransaction)


