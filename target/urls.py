from django.urls import path
from .views import *

urlpatterns = [
    # list views
    path('sales/list/', SalesListView.as_view(), name='sales-list'),
    path('sales-center/<int:pk>/detail/', SalesDetailView.as_view(), name='sales-detail'),
    path('sales-center/create/', SalesCreateView.as_view(), name='sales-create'),
    path('sales-center/<int:pk>/update/', SalesUpdateView.as_view(), name='sales-update'),
    
    path('home/', TargetHomeView.as_view(), name='target-home'),
    path('kpi/list/', KPIListView.as_view(), name='kpi-list'),
    path('kpi/create/', KPICreateView.as_view(), name='kpi-create'),
    path('kpi/<int:pk>/', KPIUpdateView.as_view(), name='kpi-update')
]
