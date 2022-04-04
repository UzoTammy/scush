from django.urls import path
from .views import *


urlpatterns = [

    path('', TemplateView.as_view(template_name='core/index.html'), name='index'),
    path('home/', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('scush/', TemplateView.as_view(template_name = 'core/scush.html'), name='scush'),
    path('company/', CompanyPageView.as_view(), name='company'),
    path('dashboard/', DashBoardView.as_view(), name='dashboard'),
    # Json model
    path('reset/help/', TemplateView.as_view(template_name='core/resetting/settings_help.html'), name='reset-help'),
    path('json/list/', JsonListView.as_view(), name='json-list'),
    path('json/<int:pk>/detail/', JsonDetailView.as_view(), name='json-detail'),
    path('json/new/', JsonCreateView.as_view(), name='json-new'),
    path('json/<int:pk>/update/', JsonUpdateView.as_view(), name='json-update'),
    path('json/<int:pk>/<str:key>/', JsonCategoryKeyView.as_view(), name='json-cat-key'),
    path('json/<int:id>/<str:key>/new/', JsonCategoryKeyValueCreateView.as_view(), name='json-cat-key-new'),
    path('json/<int:id>/<str:key>/<str:value>/', JsonCategoryKeyValueUpdateView.as_view(), name='json-cat-key-value'),

]

