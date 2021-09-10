from django.urls import path
from pdf.views import *


urlpatterns = [
    path('customers/list/', CustomerView.as_view(), name='pdf-customers-list'),
    path('payroll/list/', PayrollListView.as_view(), name='pdf-payroll-list'),
    path('staff/list/',  EmployeeListView.as_view(), name='pdf-employee-list'),
    path('apply/rejected/', RejectedApplicantList.as_view(), name='pdf-rejected-list'),
    path('payslip/', PayslipView.as_view(), name='pdf-payslip'),
    path('stock/list/', StockViewList.as_view(), name='pdf-stock-list'),
    path('staff/summary/', EmployeeSummaryView.as_view(), name='pdf-staff-summary')
]

urlpatterns += [
    path('pdf/policies/docs/', PoliciesDocView.as_view(), name='policies-docs'),
]