from django.urls import path
from .views import *


urlpatterns = [
    # list views
    path('form/failed/<str:msg>/', FormFailure.as_view(), name='failed'),
    path('article/list/', ArticleListView.as_view(), name='article-list'),
    path('issue/create/', IssueArticleCreateView.as_view(), name='issue-create'),
    path('article/create/', ArticleCreateView.as_view(), name='article-create'),
    path('article/<int:pk>/update/', ArticleUpdateView.as_view(), name='article-update'),

    # path('article/request/', ArticleRequest.as_view(), name='article-request'),
    path('request/create/', RequestCreateView.as_view(), name='request-create')
]
