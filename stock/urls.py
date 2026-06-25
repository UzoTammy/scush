from django.urls import path
from django.views.generic import TemplateView
from .views import *
from pdf.views import PriceUpdateFootNote

urlpatterns = [
    path('home/', ProductHomeView.as_view(), name='product-home'),
    path('home/fragment/no-sellout/', NoSelloutFragment.as_view(), name='home-no-sellout'),
    path('help/', TemplateView.as_view(template_name='stock/stock_help.html'), name='stock-help'),
    path('<int:pk>/detail/', ProductDetailedView.as_view(), name='product-detail'),
    path('new/', ProductCreateView.as_view(), name='product-create'),
    path('<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),

    path('price/list/', PricePageView.as_view(), name='price-list'),
    path('price/quick-update/', PriceQuickUpdateView.as_view(), name='price-quick-update'),
    path('<int:pk>/price/update/', PriceUpdate.as_view(), name='price-update'),
    path('<int:pk>/price/history/', PriceHistoryListView.as_view(), name='price-history'),
    path('<int:pk>/stock-card/', StockCardView.as_view(), name='stock-card'),
    path('<int:pk>/stock-card/add/', StockMovementCreateView.as_view(), name='stock-movement-add'),
    path('home/footnote/', PriceUpdateFootNote.as_view(), name='price-update-footnote'),
    
    path('images/', ProductImageGalleryView.as_view(), name='product-image-gallery'),
    path('stock/report/', ReportHomeView.as_view(), name='stock-report'),
    path('stock/<str:source>/', ReportStockCategory.as_view(), name='stock-report-source'),
    path('stock/<int:pk>/update/', ProductExtensionUpdateView.as_view(), name='product-ext-update'),
    path('stock/<int:pk>/detail/', ProductExtensionDetailView.as_view(), name='product-ext-detail'),
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
    path('performance/fragment/kpis/', PerformanceKpiFragment.as_view(), name='performance-kpis'),
    path('performance/fragment/top/', PerformanceTopFragment.as_view(), name='performance-top'),
    path('performance/fragment/watch/', PerformanceWatchFragment.as_view(), name='performance-watch'),

]
urlpatterns += [
    path('<str:user>/home/', StockReportHome.as_view(), name='stock-report-home'),
    path('<str:date>/<int:pk>/new/', StockReportNew.as_view(), name='stock-report-new'),
    path('<str:date>/<int:code>/update/', StockReportUpdate.as_view(), name='stock-report-record-update'),
    path('<str:date>/<int:code>/detail/', StockReportDetail.as_view(), name='stock-report-detail'),
    path('<int:pk>/status/', ProductStatusUpdate.as_view(), name='product-status'),
    # path('<int:pk>/velocity/', ProductVelocity.as_view(), name='product-velocity'),
    path('analysis/', ProductAnalysisView.as_view(), name='product-analysis'),
    path('analysis/fragment/details/', ProductAnalysisDetailFragment.as_view(), name='product-analysis-details'),
    path('balancing/', StockBalancingView.as_view(), name='stock-balancing'),
    path('balancing/fragment/tables/', StockBalancingTablesFragment.as_view(), name='stock-balancing-tables'),
    path('<int:pk>/levels/', ProductLevelUpdateView.as_view(), name='product-set-levels'),

    path('stock-count/new/', StockCountCreateView.as_view(), name='stock-count-new'),
    path('stock-count/list/', StockCountListView.as_view(), name='stock-count-list'),
    path('stock-count/<int:pk>/', StockCountDetailView.as_view(), name='stock-count-detail'),

    path('stock-transfer/', StockTransferView.as_view(), name='stock-transfer'),
    path('stock-receipt/', StockReceiptView.as_view(), name='stock-receipt'),
]

urlpatterns += [
    path('settings/categories/add/', CategoryAddView.as_view(), name='category-add'),
    path('settings/categories/<int:pk>/rename/', CategoryRenameView.as_view(), name='category-rename'),
    path('settings/categories/<int:pk>/toggle/', CategoryToggleView.as_view(), name='category-toggle'),
    path('settings/categories/<int:pk>/remove/', CategoryRemoveView.as_view(), name='category-remove'),

    path('settings/sources/add/', SourceAddView.as_view(), name='source-add'),
    path('settings/sources/<str:pk>/rename/', SourceRenameView.as_view(), name='source-rename'),
    path('settings/sources/<str:pk>/toggle/', SourceToggleView.as_view(), name='source-toggle'),
    path('settings/sources/<str:pk>/remove/', SourceRemoveView.as_view(), name='source-remove'),
    path('settings/sources/<str:pk>/details/', SourceDetailUpdateView.as_view(), name='source-update-details'),

]

urlpatterns += [
    path('material-centers/', MaterialCenterListView.as_view(), name='material-center-list'),
    path('material-centers/add/', MaterialCenterCreateView.as_view(), name='material-center-add'),
    path('material-centers/<int:pk>/edit/', MaterialCenterUpdateView.as_view(), name='material-center-update'),
    path('material-centers/<int:pk>/remove/', StockLocationRemoveView.as_view(), name='material-center-remove'),
]
