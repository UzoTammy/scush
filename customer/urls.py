from django.urls import path
from .views import *

urlpatterns = [
    path('home/', CustomerHomeView.as_view(), name='customer-home'),
    path('list/', CustomerListView.as_view(), name='customer-list-all'),
    path('<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('new/', CustomerCreateView.as_view(), name='customer-create'),
    path('<int:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
    path('request/home/', RequestHome.as_view(), name='request-home')
]

urlpatterns += [
    path('csv/customers/', CSVPart.as_view(), name='customer-csv'),
    path('csv/<int:id>/customer/', CSVCustomerDetail.as_view(), name='CSV-customer-detail'),
]
