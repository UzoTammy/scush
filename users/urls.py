from django.urls import path
from .views import *

urlpatterns = [
        path('list/', UsersListView.as_view(), name='users-list'),
]
