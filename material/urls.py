from django.urls import path
from .views import *


urlpatterns = [
    # list views
    path('form/failed/<str:msg>/', FormFailure.as_view(), name='failed'),
    path('article/list/', ArticleListView.as_view(), name='article-list'),
    path('issue/<int:pk>/create/', IssueArticleCreateView.as_view(), name='issue-create'),
    path('article/create/', ArticleCreateView.as_view(), name='article-create'),
    path('article/<int:pk>/update/', ArticleUpdateView.as_view(), name='article-update'),

    path('request/create/', RequestCreateView.as_view(), name='request-create'),
    path('article/request/<int:pk>/dissapprove/', ArticleRequestDisapprove.as_view(), name='article-request-disapprove'), 
]
