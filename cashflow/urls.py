from django.urls import path
from . import views

urlpatterns = [
    # Documentation and guide
    path('', views.CashflowHomeView.as_view(), name='cashflow-home'),
    path('bank/account/new', views.BankAccountCreateView.as_view(), name='bank-account-new'),
    path('cash/collect', views.CashCollectCreateView.as_view(), name='cashflow-cash-collect'),
    path('cash/deposit', views.CashDepositCreateView.as_view(), name='cashflow-deposit'),
    path('cash/transfer/', views.InterCashTransferView.as_view(), name='cashflow-intercash'),
    path('withdrawal/request', views.WithdrawalRequestView.as_view(), name='withdrawal-request'),
    path('interbank/transfer', views.InterbankTransferView.as_view(), name='interbank-transfer'),
    path('current/balance/<pk>/', views.CurrentBalanceUpdateView.as_view(), name='current-balance'),
    path('disable/account/<pk>/', views.DisableAccountView.as_view(), name='disable-account'),
    path('approve/withdrawal/<int:pk>', views.ApproveWithdrawalView.as_view(), name='approve-withdrawal'),
    path('administer/withdrawal/<int:pk>', views.AdministerWithdrawalView.as_view(), name='administer-withdrawal'),
    path('bank/transfer/', views.BankTransferView.as_view(), name='bank-transfer'),
    path('bank/charges', views.BankChargesView.as_view(), name='bank-charges'),
    path('bank-statment/<str:pk>/', views.BankStatementView.as_view(), name='bank-statement'),
    path('disburse-cash/', views.DisburseCashView.as_view(), name='disburse-cash'),
    path('cash-center/create/', views.CashCenterCreateView.as_view(), name='cash-center-create'),
    path('cash-statement/<int:pk>/', views.CashStatementView.as_view(), name='cash-statement'),

    path('confirm-duplicate/', views.ConfirmDuplicateView.as_view(), name='confirm-duplicate'),
    
    
]

