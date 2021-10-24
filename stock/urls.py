from django.urls import path
from .views import *

urlpatterns = [
    path('see-me/', MyFirstView.as_view(), name='see-me'),
    path('products/home/', ProductHomeView.as_view(), name='product-home'),
    path('products/list/', ProductListView.as_view(), name='product-list'),
    path('product/<int:pk>/detail/', ProductDetailedView.as_view(), name='product-detail'),
    path('product/new/', ProductCreateView.as_view(), name='product-create'),
    path('product/<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('product/<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('product/price/list/', PricePageView.as_view(), name='price-list'),
    path('product/<int:pk>/price/update/', PriceUpdate.as_view(), name='price-update'),
    
]
