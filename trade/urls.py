from django.urls import path
from .views import *

urlpatterns = [
        path('email-sample/', EmailSample.as_view(), name='email-sample'),
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
        
]

urlpatterns += [
        path('bs/create/', BSCreateView.as_view(), name='bs-create'),
        path('bs/<int:pk>/detail/', BSDetailView.as_view(), name='trade-bs-detail'),
        path('bs/list/', BSListView.as_view(), name='trade-bs-list'),
        path('bs/<int:pk>/update/', BSUpdateView.as_view(), name='trade-bs-update'),
        # path('daily/PL/report/', PLDailyReportView.as_view(), name='daily-pl-report'),    
]
