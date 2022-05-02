from django.urls import path
from .views import *

urlpatterns = [
    path('list/', PostListView.as_view(), name='post-list'),
    path('new/', PostCreateView.as_view(), name='post-create'),
    path('<int:pk>/detail/', PostDetailView.as_view(), name='post-detail'),
    path('<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    
]