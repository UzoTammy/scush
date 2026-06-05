from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('',           views.JobListView.as_view(),   name='job-list'),
    path('<int:pk>/',  views.JobDetailView.as_view(), name='job-detail'),

    # HR management
    path('manage/',            views.JobManageView.as_view(), name='job-manage'),
    path('create/',            views.JobCreateView.as_view(), name='job-create'),
    path('<int:pk>/edit/',     views.JobUpdateView.as_view(), name='job-update'),
    path('<int:pk>/toggle/',   views.job_toggle_status,       name='job-toggle'),
]
