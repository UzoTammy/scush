from django.urls import path
from .views import *

urlpatterns = [
    # list views
    path('sales/list/', SalesListView.as_view(), name='sales-list'),
    path('sales-center/<int:pk>/detail/', SalesDetailView.as_view(), name='sales-detail'),
    path('sales-center/create/', SalesCreateView.as_view(), name='sales-create'),
    path('sales-center/<int:pk>/update/', SalesUpdateView.as_view(), name='sales-update'),
    
    path('kpi/home/', TargetHomeView.as_view(), name='target-home'),
    path('kpi/list/', KPITargetListView.as_view(), name='target-list'),
    path('kpi/create/', KPITargetCreateView.as_view(), name='target-create'),
]
