from django.urls import path
from .views import *

urlpatterns = [
    # list views
    path('sales-center/list/', SalesCenterListView.as_view(), name='sales-center-list'),
    path('sales-center/<int:pk>/detail/', SalesCenterDetailView.as_view(), name='sales-center-detail'),
    path('sales-center/create/', SalesCenterCreateView.as_view(), name='sales-center-create'),
    path('sales-center/<int:pk>/update/', SalesCenterUpdateView.as_view(), name='sales-center-update')
]
