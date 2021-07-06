from django.urls import path
from . import views
from .views import (StaffListView,
                    StaffDetailView,
                    StaffCreateView,
                    StaffUpdateView,
                    StaffTerminate,
                    CreditNoteListView,
                    CreditNoteCreateView,
                    DebitNoteListView,
                    DebitNoteCreateView,
                    StartGeneratePayroll,
                    GeneratePayroll,
                    RegeneratePayroll,
                    RegeneratedPayroll,
                    SalaryPayment,
                    Payslip,
                    PayrollStatement,
                    StaffListPrivateView)

urlpatterns = [
    path('staff/', StaffListView.as_view(), name='staff-list'),
    path('staff/<int:pk>/detailed/', StaffDetailView.as_view(), name='employee-detail'),
    path('staff/<int:pk>/update/', StaffUpdateView.as_view(), name='employee-update'),
    path('staff/new/<int:pk>/', StaffCreateView.as_view(), name='employee-create'),
    path('staff/private/', StaffListPrivateView.as_view(), name='employee-list-private'),
    path('staff/terminate/<int:pk>/', StaffTerminate.as_view(), name='employee-terminate'),
    ]

urlpatterns += [
    path('payroll/credit/', CreditNoteListView.as_view(), name='credit-list'),
    path('payroll/credit-note/new/', CreditNoteCreateView.as_view(), name='credit-create'),
    path('payroll/debit/', DebitNoteListView.as_view(), name='debit-list'),
    path('payroll/debit-note/new/', DebitNoteCreateView.as_view(), name='debit-create'),
    path('payroll/start/generate/salary/', StartGeneratePayroll.as_view(), name='salary'),
    path('payroll/generate/<period>/', GeneratePayroll.as_view(), name='generate_payroll'),
    path('payroll/regenerate/', RegeneratePayroll.as_view(), name='regenerate-payroll'),
    path('payroll/regenerated/', RegeneratedPayroll.as_view(), name='regenerated-payroll'),
    path('payroll/start-pay/', SalaryPayment.as_view(), name='start-pay'),
    path('payroll/pay-salary/<int:pk>/', Payslip.as_view(), name='pay-salary'),
    path('payroll/<int:pk>/statement/', PayrollStatement.as_view(), name='payroll-statement'),
]
