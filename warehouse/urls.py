from django.urls import path
from .views import (
    DisableStoreAndAccount, HomeView, StoresListView, StoreHelpView, StoresDetailView,
     StoresCreateView, StoresUpdateView,
     BankAccountCreate, BankAccountUpdate, BankAccountDetail,
     StoreLevyCreateView, StoreLevyListView, StoreLevyUpdateView,
     PayRentView, UpdateRentView, RentListView
     )

urlpatterns = [
    path('home/', HomeView.as_view(), name='warehouse-home'),
    path('list/all/', StoresListView.as_view(), name='warehouse-list-all'),
    path('help/', StoreHelpView.as_view(), name='warehouse-help'),
    path('<int:pk>/', StoresDetailView.as_view(), name='warehouse-detail'),
    path('new/', StoresCreateView.as_view(), name='warehouse-create'),
    path('update/<int:pk>/', StoresUpdateView.as_view(), name='warehouse-update'),
    path('bank/<int:pk>/add/', BankAccountCreate.as_view(), name='warehouse-bank-create'),
    path('bank/<int:pk>/update/', BankAccountUpdate.as_view(), name='warehouse-bank-update'),
    path('bank/<int:pk>/detail/', BankAccountDetail.as_view(), name='warehouse-bank-detail'),
    # path('<int:pk>/payment/', StoresDetailView.as_view(), name='payment'),
    path('<int:pk>/store/bank', DisableStoreAndAccount.as_view(), name='disable-store-bank'),

    path('levy/create/', StoreLevyCreateView.as_view(), name='store-levy-create'),
    path('levy/list/', StoreLevyListView.as_view(), name='store-levy-list'),
    path('levy/update/<int:pk>/', StoreLevyUpdateView.as_view(), name='store-levy-update'),

    path('pay/rent/<int:pk>/', PayRentView.as_view(), name='store-pay-rent'),
    path('renew/rent/<int:pk>/', UpdateRentView.as_view(), name='renew-rent-update'),
    path('rent/list/', RentListView.as_view(), name='store-rent-list')
       
]