from django.urls import path
from .views import (StaffMainPageView, StaffListView, StaffPoliciesView, StaffListPicturesView,
                    StaffDetailView, StaffUpdateView, StaffCreateView, StaffListPrivateView,
                    StaffTerminate, StaffSuspend, StaffReassign, StaffPermit, RequestPermissionView,
                    StaffSalaryChange, StaffChangeManagement, TerminatedStaffListView, PKResetView,
                    PKResetPayroll, AddGratuity, GratuityListView, GratuityDetailView, GratuityUpdateView,
                    GratuityListViewOneStaff, UserHandleCreateView, CreditNoteListView, CreditDetailView,
                    CreditNoteCreateView, CreditUpdateView, DebitNoteListView, DebitNoteDetailView, DebitUpdateView,
                    DebitNoteCreateView, PayrollHome, PayrollViews, GeneratePayroll, RegeneratedPayroll,
                    RegeneratePayroll, SalaryPayment, Payslip, PayslipStatement, PayrollSummaryView,
                    ModifyGeneratedPayroll, MakeOutstandingValueZero, UpdateTax, TaxList, RequestPermissionUpdateView,
                    RequestPermissionListView, PermissionFromRequest, RequestPermissionDisapprove, staffWelfare,
                    WelfareSupportList,WelfareSupportListViewOneStaff, PayrollView, ProcessEmployeeUpdateView,
                    BackView, NextView)


urlpatterns = [
    path('home/', StaffMainPageView.as_view(), name='staff-home'),
    path('all/', StaffListView.as_view(), name='staff-list'),
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
    path('request/permission/<int:pk>/', RequestPermissionView.as_view(), name='request-permission'), # working
    path('salary-change/<int:pk>/', StaffSalaryChange.as_view(), name='employee-salary-change'),
    path('change/management/<int:pk>/', StaffChangeManagement.as_view(), name='employee-management'),
    path('home/<str:staff_category>/', TerminatedStaffListView.as_view(), name='terminated'),
    path('pk-reset/', PKResetView.as_view(), name='pk-reset'),
    path('pk-reset/payroll/', PKResetPayroll.as_view(), name='pk-reset-payroll'),
    
    path('employee/<int:pk>/balance/', AddGratuity.as_view(), name='employee-balance'),
    path('employee/balance/list/', GratuityListView.as_view(), name='employee-balance-list'),
    path('employee/balance/<int:pk>/detail/', GratuityDetailView.as_view(), name='employee-balance-detail'),
    path('employee/balance/<int:pk>/update/', GratuityUpdateView.as_view(), name='employee-balance-update'),
    path('employee/<int:pk>/gratity/', GratuityListViewOneStaff.as_view(), name='employee-gratuity-list'),
    path('user/<int:pk>/create/', UserHandleCreateView.as_view(), name='create-user')
    ]
    
urlpatterns += [
    path('payroll/credit/', CreditNoteListView.as_view(), name='credit-list'),
    path('payroll/credit/<int:pk>/detail/', CreditDetailView.as_view(), name='credit-detail'),
    path('payroll/credit-note/new/', CreditNoteCreateView.as_view(), name='credit-create'),
    path('payroll/credit/<int:pk>/update/', CreditUpdateView.as_view(), name='credit-update'),
    path('payroll/debit/', DebitNoteListView.as_view(), name='debit-list'),
    path('payroll/debit/<int:pk>/detail/', DebitNoteDetailView.as_view(), name='debit-detail'),
    path('payroll/debit/<int:pk>/update/', DebitUpdateView.as_view(), name='debit-update'),
    path('payroll/debit-note/new/', DebitNoteCreateView.as_view(), name='debit-create'),
    path('payroll/start/generate/salary/', PayrollHome.as_view(), name='salary'),
    path('payroll/views/<str:period>/', PayrollViews.as_view(), name='payroll-view'),
    path('payroll/generate/<str:period>/', GeneratePayroll.as_view(), name='generate-payroll'),
    path('payroll/regenerate/', RegeneratePayroll.as_view(), name='regenerate-payroll'),
    path('payroll/regenerated/', RegeneratedPayroll.as_view(), name='regenerated-payroll'),
    path('payroll/start-pay/', SalaryPayment.as_view(), name='start-pay'),
    path('payroll/pay-salary/<int:pk>/', Payslip.as_view(), name='pay-salary'),
    path('payroll/<int:pk>/statement/', PayslipStatement.as_view(), name='payroll-statement'),
    path('payroll/summary/<str:summary_period>/', PayrollSummaryView.as_view(), name='payroll-summary'),
    path('payroll/modify/', ModifyGeneratedPayroll.as_view(), name='payroll-modify'),
    path('payroll/modify/<int:pk>/outstanding/', MakeOutstandingValueZero.as_view(), name='payroll-modify-outstanding'),
    path('payroll/update/tax/', UpdateTax.as_view(), name='update-tax'),
    path('payroll/<int:pk>/balance/', GratuityListViewOneStaff.as_view(), name='balance-view'),
    path('payroll/tax/list/', TaxList.as_view(), name='tax-list'),
    
    # payroll process 
    path('payroll/process/', PayrollView.as_view(), name='payroll-process'),
    path('payroll/process/employee/update/', ProcessEmployeeUpdateView.as_view(), name='payroll-process-employee-update'),
    path('payroll/back/', BackView.as_view(), name='payroll-back'),
    path('payroll/next/', NextView.as_view(), name='payroll-next')
]

urlpatterns += [
    # path('request/permission/create/', RequestPermissionCreateView.as_view(), name='request-permission-create'),
    path('request/permission/<int:pk>/update/', RequestPermissionUpdateView.as_view(), name='request-permission-update'),
    path('request/permission/list/', RequestPermissionListView.as_view(), name='request-permission-list'),
    path('permission/from/<int:pk>/request/', PermissionFromRequest.as_view(), name='permission-from-request'),
    path('request/permission/<int:pk>/disapprove/', RequestPermissionDisapprove.as_view(), name='request-permission-disapprove'),
    # path('terminated/<int:pk>/detail/', StaffTerminateDetailView.as_view(), name='terminated-detail')
]

urlpatterns += [
    path('welfare/<int:pk>/', staffWelfare.as_view(), name='staff-welfare'),
    path('welfare/list/', WelfareSupportList.as_view(), name='welfare-support-list'),
    path('welfare/list/<str:pk>/one-staff/', WelfareSupportListViewOneStaff.as_view(), name='welfare-list-detail'),
]