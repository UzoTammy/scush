from django.urls import path
from . import views

urlpatterns = [
    # ── Public: job listings ──────────────────────────────────────────────────
    path('',          views.JobListView.as_view(),   name='job-list'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),

    # ── HR: job posting management ────────────────────────────────────────────
    path('manage/',          views.JobManageView.as_view(), name='job-manage'),
    path('create/',          views.JobCreateView.as_view(), name='job-create'),
    path('<int:pk>/edit/',   views.JobUpdateView.as_view(), name='job-update'),
    path('<int:pk>/toggle/', views.job_toggle_status,       name='job-toggle'),

    # ── HR: application management ────────────────────────────────────────────
    path('applications/',                    views.ApplicationListView.as_view(), name='app-list'),
    path('applications/new/',                views.ApplicationInitView.as_view(), name='app-init'),
    path('applications/<int:pk>/',           views.ApplicationDetailView.as_view(), name='app-detail'),
    path('applications/<int:pk>/status/',    views.application_set_status, name='app-status'),
    path('applications/<int:pk>/guarantor/', views.guarantor_request,      name='app-guarantor-request'),
    path('applications/<int:pk>/review/',          views.guarantor_review,       name='app-guarantor-review'),
    path('applications/<int:pk>/extend/',          views.extend_applicant_link,  name='app-extend-link'),
    path('applications/<int:pk>/extend-guarantor/', views.extend_guarantor_link, name='app-extend-guarantor'),

    # ── Public: token-based applicant form ────────────────────────────────────
    path('apply/<uuid:token>/',      views.applicant_form,      name='applicant-form'),
    path('apply/<uuid:token>/done/', views.applicant_submitted, name='applicant-submitted'),

    # ── Public: token-based guarantor form (Letter of Indemnity) ─────────────
    path('guarantee/<uuid:token>/',      views.guarantor_form,      name='guarantor-form'),
    path('guarantee/<uuid:token>/done/', views.guarantor_submitted, name='guarantor-submitted'),
]
