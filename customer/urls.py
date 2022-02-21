from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('', TemplateView.as_view(template_name='customer/index.html'), name='index'),
    path('scush/', TemplateView.as_view(template_name = 'customer/scush.html'), name='scush'),
    path('home/', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('survey/', ViewSurvey.as_view(), name='survey'),
    path('company/', views.company, name='company'),
    path('customer/home/', CustomerHomeView.as_view(), name='customer-home'),
    path('customer/list/', CustomerListView.as_view(), name='customer-list-all'),
    path('customer/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customer/new/', CustomerCreateView.as_view(), name='customer-create'),
    path('customer/<int:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('customer/<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
    path('request/home/', RequestHome.as_view(), name='request-home')
]

urlpatterns += [
    path('csv/customers/', CSVPart.as_view(), name='customer-csv'),
    path('csv/<int:id>/customer/', CSVCustomerDetail.as_view(), name='CSV-customer-detail'),
]