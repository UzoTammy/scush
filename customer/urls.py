from django.urls import path
from . import views
from .views import (CustomerListView,
                    CustomerDetailView,
                    CustomerCreateView,
                    CustomerUpdateView,
                    CustomerDeleteView,
                    CSVPart,
                    CSVCustomerDetail)


urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('company/', views.company, name='company'),
    path('customer/', CustomerListView.as_view(), name='customer-list'),
    path('customer/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customer/new/', CustomerCreateView.as_view(), name='customer-create'),
    path('customer/<int:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('customer/<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
]

urlpatterns += [
    path('csv/customers/', CSVPart.as_view(), name='csv-customers'),
    path('csv/<int:id>/customer/', CSVCustomerDetail.as_view(), name='CSV-customer-detail'),
]