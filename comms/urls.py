from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListView.as_view(), name='comms-post-list'),
    path('posts/new/', views.PostCreateView.as_view(), name='comms-post-create'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='comms-post-detail'),
    path('posts/<int:pk>/update/', views.PostUpdateView.as_view(), name='comms-post-update'),

    path('projects/', views.ProjectListView.as_view(), name='comms-project-list'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='comms-project-create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='comms-project-detail'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='comms-project-update'),
    path('projects/<int:pk>/tasks/new/', views.TaskCreateView.as_view(), name='comms-task-create'),

    path('tasks/', views.TaskListView.as_view(), name='comms-task-list'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='comms-task-update'),
    path('tasks/<int:pk>/status/', views.TaskStatusUpdateView.as_view(), name='comms-task-status'),

    path('polls/', views.PollListView.as_view(), name='comms-poll-list'),
    path('polls/new/', views.PollCreateView.as_view(), name='comms-poll-create'),
    path('polls/<int:pk>/', views.PollDetailView.as_view(), name='comms-poll-detail'),
    path('polls/<int:pk>/vote/', views.PollVoteView.as_view(), name='comms-poll-vote'),
    path('polls/<int:pk>/results/', views.PollResultsView.as_view(), name='comms-poll-results'),
    path('polls/<int:pk>/toggle/', views.PollToggleActiveView.as_view(), name='comms-poll-toggle'),
    path('poll/<uuid:token>/', views.PollPublicAccessView.as_view(), name='comms-poll-public'),
    path('poll/<uuid:token>/vote/', views.PollPublicVoteView.as_view(), name='comms-poll-public-vote'),
]
