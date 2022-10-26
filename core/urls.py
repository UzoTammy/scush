from django.urls import path
from .views import *
from . import views
# from django.contrib.auth import views as auth_views
# from django.contrib.auth.forms import PasswordChangeForm

urlpatterns = [
    # Documentation and guide
    path('', views.index, name='index'),
    path('developer/', views.developer_login, name='developer'),

    path('scush/', ScushView.as_view(), name='scush'),
    path('home/', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('company/', CompanyPageView.as_view(), name='company'),
    path('dashboard/', DashBoardView.as_view(), name='dashboard'),
    path('policies/', PoliciesView.as_view(), name='policies'),
    # Json model
    path('json/list/', JsonListView.as_view(), name='json-list'),
    path('json/<int:pk>/detail/', JsonDetailView.as_view(), name='json-detail'),
    path('json/new/', JsonCreateView.as_view(), name='json-new'),
    path('json/<int:pk>/update/', JsonUpdateView.as_view(), name='json-update'),
    path('json/<int:pk>/<str:key>/', JsonCategoryKeyView.as_view(), name='json-cat-key'),
    path('json/<int:id>/<str:key>/new/', JsonCategoryKeyValueCreateView.as_view(), name='json-cat-key-new'),
    path('json/<int:id>/<str:key>/<str:value>/', JsonCategoryKeyValueUpdateView.as_view(), name='json-cat-key-value'),
    path('reset/help/', TemplateView.as_view(template_name='core/resetting/settings_help.html'), name='reset-help'),
    path('mail/<str:target>/<str:kpi>/', KPIMailSend.as_view(), name='kpi_mail'),
    
    path('practice/', PracticeView.as_view(), name='practice'),
    
]

