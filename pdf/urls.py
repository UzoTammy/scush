from django.urls import path
from pdf.views import (CustomerView,
                       PayrollListView,
                       EmployeeListView,
                       RejectedApplicantList,
                       PayslipView,
                       PoliciesDocView,
                       StockViewList)


urlpatterns = [
    path('customers/list/', CustomerView.as_view(), name='pdf-customers-list'),
    path('payroll/list/', PayrollListView.as_view(), name='pdf-payroll-list'),
    path('staff/list/',  EmployeeListView.as_view(), name='pdf-employee-list'),
    path('apply/rejected/', RejectedApplicantList.as_view(), name='pdf-rejected-list'),
    path('payslip/', PayslipView.as_view(), name='pdf-payslip'),

    path('stock/list/', StockViewList.as_view(), name='pdf-stock-list')
]

urlpatterns += [
    path('pdf/policies/docs/', PoliciesDocView.as_view(), name='policies-docs'),
]