from django.urls import path
from . import views
from .views import (DeliveryHomeView,
                    DeliveryCreateView,
                    DeliveryListView,
                    DeliveryDetailView,
                    DeliveryArriveUpdateView,
                    DeliveryReturnUpdateView,
                    DeliveryConfirm,
                    DeliveryCredit,
                    DeliveryRemark,

                    )

urlpatterns = [
    # list views
    path('home/', DeliveryHomeView.as_view(), name='delivery-home'),
    path('new/', DeliveryCreateView.as_view(), name='delivery-create'),
    path('list/', DeliveryListView.as_view(), name='delivery-list'),

    path('<int:pk>/', DeliveryDetailView.as_view(), name='delivery-detail'),
    path('arrive/<int:pk>/', DeliveryArriveUpdateView.as_view(), name='delivery-arrive'),
    path('return/<int:pk>/', DeliveryReturnUpdateView.as_view(), name='delivery-return'),
    path('confirm/<int:pk>/', DeliveryConfirm.as_view(), name='delivery-confirm'),
    path('credit/<int:pk>/', DeliveryCredit.as_view(), name='delivery-credit'),
    path('remark/<int:pk>/', DeliveryRemark.as_view(), name='delivery-remark'),

]
