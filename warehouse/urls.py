from django.urls import path
from .views import *

urlpatterns = [
    path('stores/home/', HomeView.as_view(), name='warehouse-home'),
    path('stores/list/all/', StoresListView.as_view(), name='warehouse-list-all'),
    path('stores/help/', StoreHelpView.as_view(), name='warehouse-help'),
    path('stores/<int:pk>/', StoresDetailView.as_view(), name='warehouse-detail'),
    path('stores/new/', StoresCreateView.as_view(), name='warehouse-create'),
    path('stores/update/<int:pk>/', StoresUpdateView.as_view(), name='warehouse-update'),
    path('stores/pay/<int:pk>/rent/', PayRent.as_view(), name='warehouse-pay-rent')
]