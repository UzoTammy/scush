from django.urls import path
from .views import *

urlpatterns = [
        path('list/', UsersListView.as_view(), name='users-list'),
        path('group/list/', UserGroupView.as_view(), name='group-list')
]
