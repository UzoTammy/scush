from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('home/', StaffMainPageView.as_view(), name='staff-home'),
    path('all/', StaffListView.as_view(), name='staff-list'),
    path('scush/', StaffScushView.as_view(), name='staff-scush'),
    path('policies/', StaffPoliciesView.as_view(), name='staff-policies'),
    path('photos/', StaffListPicturesView.as_view(), name='staff-pictures'),
    path('<int:pk>/detail/', StaffDetailView.as_view(), name='employee-detail'),
    path('<int:pk>/update/', StaffUpdateView.as_view(), name='employee-update'),
    path('new/<int:pk>/', StaffCreateView.as_view(), name='employee-create'),
    path('private/', StaffListPrivateView.as_view(), name='employee-list-private'),
    path('terminate/<int:pk>/', StaffTerminate.as_view(), name='employee-terminate'),
    path('reassign/<int:pk>/', StaffReassign.as_view(), name='employee-reassign'),
    path('suspend/<int:pk>/', StaffSuspend.as_view(), name='employee-suspend'),
    path('permit/<int:pk>/', StaffPermit.as_view(), name='employee-permit'),
    path('salary-change/<int:pk>/', StaffSalaryChange.as_view(), name='employee-salary-change'),
    path('home/<str:staff_category>/', StaffViews.as_view(), name='terminated'),
    path('pk-reset/', PKResetView.as_view(), name='pk-reset'),
    path('pk-reset/payroll/', PKResetPayroll.as_view(), name='pk-reset-payroll'),
    ]

urlpatterns += [
    path('payroll/credit/', CreditNoteListView.as_view(), name='credit-list'),
    path('payroll/credit-note/new/', CreditNoteCreateView.as_view(), name='credit-create'),
    path('payroll/debit/', DebitNoteListView.as_view(), name='debit-list'),
    path('payroll/debit-note/new/', DebitNoteCreateView.as_view(), name='debit-create'),
    path('payroll/start/generate/salary/', StartGeneratePayroll.as_view(), name='salary'),
    path('payroll/views/<str:period>/', PayrollViews.as_view(), name='payroll-view'),
    path('payroll/generate/<str:period>/', GeneratePayroll.as_view(), name='generate-payroll'),
    path('payroll/regenerate/', RegeneratePayroll.as_view(), name='regenerate-payroll'),
    path('payroll/regenerated/', RegeneratedPayroll.as_view(), name='regenerated-payroll'),
    path('payroll/start-pay/', SalaryPayment.as_view(), name='start-pay'),
    path('payroll/pay-salary/<int:pk>/', Payslip.as_view(), name='pay-salary'),
    path('payroll/<int:pk>/statement/', PayrollStatement.as_view(), name='payroll-statement'),
    path('payroll/summary/<str:summary_period>/', PayrollSummaryView.as_view(), name='payroll-summary'),
    path('payroll/modify/', ModifyGeneratedPayroll.as_view(), name='payroll-modify'),
    path('payroll/modify/<int:pk>/outstanding/', MakeOutstandingValueZero.as_view(), name='payroll-modify-outstanding')
]
