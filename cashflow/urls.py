from django.urls import path
from . import views
# from django.contrib.auth import views as auth_views
# from django.contrib.auth.forms import PasswordChangeForm

urlpatterns = [
    # Documentation and guide
    path('', views.CashflowHomeView.as_view(), name='cashflow-home'),
    path('bank/account/new', views.BankAccountCreateView.as_view(), name='bank-account-new'),
    path('cash/collect', views.CashCollectCreateView.as_view(), name='cashflow-cash-collect'),
    path('cash/deposit', views.CashDepositCreateView.as_view(), name='cashflow-deposit'),
    path('disburse/', views.DisburseView.as_view(), name='cashflow-disburse'),
    path('withdrawal/request', views.WithdrawalRequestView.as_view(), name='withdrawal-request'),
    path('interbank/transfer', views.InterbankTransferView.as_view(), name='interbank-transfer'),
    path('current/balance/<pk>/', views.CurrentBalanceUpdateView.as_view(), name='current-balance'),
    path('disable/account/<pk>/', views.DisableAccountView.as_view(), name='disable-account'),
    path('approve/withdrawal/<int:pk>', views.ApproveWithdrawalView.as_view(), name='approve-withdrawal'),
    path('administer/withdrawal/<int:pk>', views.AdministerWithdrawalView.as_view(), name='administer-withdrawal'),
     
]

