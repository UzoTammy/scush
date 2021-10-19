from django.urls import path
from .views import *

urlpatterns = [
        path('home/', TradeHome.as_view(), name='trade-home'),
        path('trading-account/', TradeTradingReport.as_view(), name='trade-trading-account'),
        path('monthly/create/', TradeMonthlyCreateView.as_view(), name='trade-create'),
        path('monthly/list/', TradeMonthlyListView.as_view(), name='trade-list'),
        path('monthly/<int:pk>/detail/', TradeMonthlyDetailView.as_view(), name='trade-detail'),
        path('monthly/<int:pk>/update/', TradeMonthlyUpdateView.as_view(), name='trade-update'),
] 

urlpatterns += [
        path('daily/create/', TradeDailyCreateView.as_view(), name='trade-daily-create'),
        path('daily/list/', TradeDailyListView.as_view(), name='trade-daily-list'),
        path('daily/<int:pk>/detail/', TradeDailyDetailView.as_view(), name='trade-daily-detail'),
        path('daily/<int:pk>/update/', TradeDailyUpdateView.as_view(), name='trade-daily-update'),
        path('daily/PL/report/', PLDailyReportView.as_view(), name='daily-pl-report'),
        path('dashboard/', DashBoardView.as_view(), name='dashboard'),
]
