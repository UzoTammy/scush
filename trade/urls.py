from django.urls import path
from .views import *

urlpatterns = [
        path('home/', TradeHome.as_view(), name='trade-home'),
        path('create/', TradeCreate.as_view(), name='trade-create'),
        path('list/', TradeList.as_view(), name='trade-list'),
        path('detail/<int:pk>/', TradeDetail.as_view(), name='trade-detail'),
        path('update/<int:pk>/', TradeUpdate.as_view(), name='trade-update'),
    ]