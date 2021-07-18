from django.contrib import admin
from .models import (Employee,
                     StaffStatement,
                     CreditNote,
                     DebitNote,
                     Payroll,
                     Terminate,
                     Reassign)

# Register your models here.
admin.site.register(Employee)
admin.site.register(StaffStatement)
admin.site.register(CreditNote)
admin.site.register(DebitNote)
admin.site.register(Payroll)
admin.site.register(Terminate)
admin.site.register(Reassign)


