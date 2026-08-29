from django.urls import path
from . import views
from .views import *

urlpatterns = [
        path('list/', UsersListView.as_view(), name='users-list'),
        path('group/list/', UserGroupView.as_view(), name='group-list'),
        path('invite/', views.invite_create, name='user-invite-create'),
        path('invite/<int:pk>/delete/', views.invite_delete, name='user-invite-delete'),
        path('invite/<uuid:token>/', views.register_via_invite, name='register-invite'),
]
