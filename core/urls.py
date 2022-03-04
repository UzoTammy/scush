from django.urls import path
from .views import *

urlpatterns = [

    path('', TemplateView.as_view(template_name='core/index.html'), name='index'),
    path('home/', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('scush/', TemplateView.as_view(template_name = 'core/scush.html'), name='scush'),
    path('company/', CompanyPageView.as_view(), name='company'),
    path('dashboard/', DashBoardView.as_view(), name='dashboard'),
    
]

