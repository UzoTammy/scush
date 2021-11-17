from django.contrib import admin
from .models import (Employee,
                     StaffStatement,
                     CreditNote,
                     DebitNote,
                     Payroll,
                     Terminate,
                     Reassign,
                     Suspend,
                     Permit,
                     SalaryChange, 
                     EmployeeBalance,
                     RequestPermission
                     )

# Register your models here.

class PayrollAdmin(admin.ModelAdmin):
    list_display = ['id', 'staff', 'period', 'balance', 'salary']


admin.site.register(Employee)
admin.site.register(StaffStatement)
admin.site.register(CreditNote)
admin.site.register(DebitNote)
admin.site.register(Payroll, PayrollAdmin)
admin.site.register(Terminate)
admin.site.register(Reassign)
admin.site.register(Suspend)
admin.site.register(Permit)
admin.site.register(SalaryChange)
admin.site.register(EmployeeBalance)
admin.site.register(RequestPermission)



