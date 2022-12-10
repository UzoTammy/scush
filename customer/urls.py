from django.urls import path
from .views import *

urlpatterns = [
    path('home/', CustomerHomeView.as_view(), name='customer-home'),
    path('<str:select>/list/', CustomerListView.as_view(), name='customer-list'),
    path('<str:cluster>/cluster/', CustomerClusterView.as_view(), name='cluster-list'),
    path('<int:pk>/detail/', CustomerDetailView.as_view(), name='customer-detail'),
    path('new/', CustomerCreateView.as_view(), name='customer-create'),
    path('<int:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
    path('request/home/', RequestHome.as_view(), name='request-home'),
    path('help/', CustomerHelpView.as_view(), name='customer-help')
]

urlpatterns += [
    path('imported/csv/', CustomerProfileCSVView.as_view(), name='csv-list-view')
]

urlpatterns += [
    path('credit/view/', CustomerCreditListView.as_view(), name='customer-credit-list'),
    path('credit/<int:code>/create/', CustomerCreditCreateView.as_view(), name='customer-credit-create'),
    path('credit/<int:pk>/update/', CustomerCreditUpdateView.as_view(), name='customer-credit-update')  
]