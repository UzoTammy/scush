from django.urls import path
from .views import *
from pdf.views import PriceUpdateFootNote

urlpatterns = [
    path('see-me/', MyFirstView.as_view(), name='see-me'),
    path('product/home/', ProductHomeView.as_view(), name='product-home'),
    path('product/list/', ProductListView.as_view(), name='product-list'),
    path('product/<int:pk>/detail/', ProductDetailedView.as_view(), name='product-detail'),
    path('product/new/', ProductCreateView.as_view(), name='product-create'),
    path('product/<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('product/<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('product/price/list/', PricePageView.as_view(), name='price-list'),
    path('product/<int:pk>/price/update/', PriceUpdate.as_view(), name='price-update'),
    path('product/home/footnote/', PriceUpdateFootNote.as_view(), name='price-update-footnote')
]

urlpatterns += [
    path('product/performance/list/', ProductPerformanceListView.as_view(), name='product-performance-list'),
    path('product/performance/create/', ProductPerformanceCreateView.as_view(), name='product-performance-create'),
    path('product/performance/<int:pk>/detail/', ProductPerformanceDetailView.as_view(), name='product-performance-detail')
    
]
