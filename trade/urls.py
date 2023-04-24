from django.urls import path
from .views import *

urlpatterns = [
        path('email-sample/', EmailSample.as_view(), name='email-sample'),
        path('home/', TradeHome.as_view(), name='trade-home'),
        path('trading-account/', TradeTradingReport.as_view(), name='trade-trading-account'),
        path('monthly/create/', TradeMonthlyCreateView.as_view(), name='trade-create'),
        path('monthly/list/', TradeMonthlyListView.as_view(), name='trade-list'),
        path('monthly/<int:pk>/detail/', TradeMonthlyDetailView.as_view(), name='trade-detail'),
        path('monthly/<int:pk>/update/', TradeMonthlyUpdateView.as_view(), name='trade-update'),
] 

urlpatterns += [
        path('daily/create/', TradeDailyCreateView.as_view(), name='trade-daily-create'),
        path('daily/list/', TradeDailyListView.as_view(), name='trade-daily-list'),
        path('daily/<int:pk>/detail/', TradeDailyDetailView.as_view(), name='trade-daily-detail'),
        path('daily/<int:pk>/update/', TradeDailyUpdateView.as_view(), name='trade-daily-update'),
        path('daily/PL/report/', PLDailyReportView.as_view(), name='daily-pl-report'),
        
]

urlpatterns += [
        path('bs/create/', BSCreateView.as_view(), name='bs-create'),
        path('bs/<int:pk>/detail/', BSDetailView.as_view(), name='trade-bs-detail'),
        path('bs/list/', BSListView.as_view(), name='trade-bs-list'),
        path('bs/<int:pk>/update/', BSUpdateView.as_view(), name='trade-bs-update'),
        # path('daily/PL/report/', PLDailyReportView.as_view(), name='daily-pl-report'),    
]

urlpatterns += [
        path('weekly/report', TradeWeekly.as_view(), name='trade-weeekly'),
        path('audit/', AuditorView.as_view(), name='audit'),
]

urlpatterns += [
    path('bank-account/', BankAccountHomeView.as_view(), name='bank-account-home'),
    path('bank-account/<int:pk>/detail/', BankAccountDetailView.as_view(), name='bank-account-detail'),
    path('bank-account/list/', BankAccountListView.as_view(), name='bank-account-list'),
    path('bank-account/<int:pk>/update/', BankAccountUpdateView.as_view(), name='bank-account-update'),
    path('bank-account/add/', BankAccountCreateView.as_view(), name='bank-account-create'),
    path('bank-balance/add/', BankBalanceCreateView.as_view(), name='bank-balance-create'),
    path('bank-balance/<int:pk>/detail/', BankBalanceDetailView.as_view(), name='bank-balance-detail'),
    path('bank-balance/<int:pk>', BankBalanceUpdateView.as_view(), name='bank-balance-update'),    
    path('bank-balance/list/', BankBalanceListView.as_view(), name='bank-balance-list'),
    path('bank-account/list/admin/', BankBalanceListViewAdmin.as_view(), name='bank-balance-list-admin'),
    path('bank-balance/<int:pk>/copy/', BankBalanceCopyView.as_view(), name='bank-balance-copy'),
    
]

urlpatterns += [
    path('creditors/', CreditorHomeView.as_view(), name='creditor-home'),
    path('creditors/create/', CreditorCreateView.as_view(), name='creditor-create'),
    
]