from django.urls import path
from .views import *
from pdf.views import PriceUpdateFootNote

urlpatterns = [
    path('see-me/', MyFirstView.as_view(), name='see-me'),
    path('home/', ProductHomeView.as_view(), name='product-home'),
    path('stock-value/', StockValueView.as_view(), name='stock-value'),
    path('list/', ProductListView.as_view(), name='product-list'),
    path('tabular/', ProductTabularCreateView.as_view(), name='product-tabular'),
    path('tabular/List/', ProductTabularListView.as_view(), name='product-tabular-list'),
    path('<int:pk>/detail/', ProductDetailedView.as_view(), name='product-detail'),
    path('new/', ProductCreateView.as_view(), name='product-create'),
    path('<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('price/list/', PricePageView.as_view(), name='price-list'),
    path('<int:pk>/price/update/', PriceUpdate.as_view(), name='price-update'),
    path('home/footnote/', PriceUpdateFootNote.as_view(), name='price-update-footnote')
]

urlpatterns += [
    path('performance/list/', ProductPerformanceListView.as_view(), name='product-performance-list'),
    path('performance/create/', ProductPerformanceCreateView.as_view(), name='product-performance-create'),
    path('performance/<int:pk>/detail/', ProductPerformanceDetailView.as_view(), name='product-performance-detail')
    
]
