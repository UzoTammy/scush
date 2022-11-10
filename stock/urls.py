from django.urls import path
from .views import *
from pdf.views import PriceUpdateFootNote

urlpatterns = [
    path('home/', ProductHomeView.as_view(), name='product-home'),
    path('<int:pk>/detail/', ProductDetailedView.as_view(), name='product-detail'),
    path('new/', ProductCreateView.as_view(), name='product-create'),
    path('<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),

    path('price/list/', PricePageView.as_view(), name='price-list'),
    path('<int:pk>/price/update/', PriceUpdate.as_view(), name='price-update'),
    path('home/footnote/', PriceUpdateFootNote.as_view(), name='price-update-footnote'),
    
    path('stock/report/', ReportHomeView.as_view(), name='stock-report'),
    path('stock/<str:source>/', ReportStockCategory.as_view(), name='stock-report-source'),
    path('stock/<int:pk>/update/', ProductExtensionUpdateView.as_view(), name='product-ext-update'),
    path('stock/<int:pk>/detail/', ProductExtensionDetailView.as_view(), name='product-ext-detail'),
    path('stock/report/<str:month>/', ProductExtensionListView.as_view(), name='stock-month'),
    path('stock/report/<str:month>/<str:source>/', ProductExtensionProduct.as_view(), name='stock-report-product'),
    path('report/all-products/', StockReportAllProducts.as_view(), name='stock-report-all-products'),
    path('report/<int:pk>/a-product/', StockReportOneProducts.as_view(), name='stock-report-one-product')
]

urlpatterns += [
    path('performance/list/', ProductPerformanceListView.as_view(), name='product-performance-list'),
    path('performance/create/', ProductPerformanceCreateView.as_view(), name='product-performance-create'),
    path('performance/<int:pk>/detail/', ProductPerformanceDetailView.as_view(), name='product-performance-detail'),
    path('watchlist/home/', WatchlistHomeView.as_view(), name='watchlist-home'),
    path('watchlist/<str:action>/', WatchlistUpdateView.as_view(), name='watchlist-update'),
    path('update/<str:source>/', StockReportUpdateView.as_view(), name='stock-report-update'),
    path('add/<str:source>/', StockReportAddView.as_view(), name='stock-report-add'),
    path('performance/home/', PerformanceHome.as_view(), name='performance-home'),

]

urlpatterns += [
    path('<str:user>/home/', StockReportHome.as_view(), name='stock-report-home'),
    path('<str:date>/<int:pk>/new/', StockReportNew.as_view(), name='stock-report-new'),
    path('<str:date>/<int:code>/update/', StockReportUpdate.as_view(), name='stock-report-update'),
    path('<str:date>/<int:code>/detail/', StockReportDetail.as_view(), name='stock-report-detail'),
    path('<int:pk>/status/', ProductStatusUpdate.as_view(), name='product-status'),
    path('bulk-update/', BulkUpdateStock.as_view(), name='bulk-update-stock')
]
