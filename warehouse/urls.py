from django.urls import path
from .views import *

urlpatterns = [
    path('home/', HomeView.as_view(), name='warehouse-home'),
    path('list/all/', StoresListView.as_view(), name='warehouse-list-all'),
    path('help/', StoreHelpView.as_view(), name='warehouse-help'),
    path('<int:pk>/', StoresDetailView.as_view(), name='warehouse-detail'),
    path('new/', StoresCreateView.as_view(), name='warehouse-create'),
    path('update/<int:pk>/', StoresUpdateView.as_view(), name='warehouse-update'),
    path('pay/<int:pk>/rent/', PayRent.as_view(), name='warehouse-pay-rent'),
    path('bank/add/', BankAccountCreate.as_view(), name='warehouse-bank-create'),
    path('<int:pk>/update/', BankAccountUpdate.as_view(), name='warehouse-bank-update'),
    path('<int:pk>/payment/', StoresDetailView.as_view(), name='payment')
]