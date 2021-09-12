from django.urls import path
from . import views
from .views import (ApplyListViewPending,
                    ApplyListViewEmployed,
                    ApplyListViewRejected,
                    ApplyListView,
                    ApplyDetailView,
                    ApplyDeleteView,
                    ApplyUpdateView,
                    ApplyCreateView,
                    RejectApplicant,
                    )
from pdf.views import ApplicantListView

urlpatterns = [
    # list views
    path('apply/list/pending/', ApplyListViewPending.as_view(), name='apply-pending'),
    path('apply/list/employed/', ApplyListViewEmployed.as_view(), name='apply-employed'),
    path('apply/list/rejected/', ApplyListViewRejected.as_view(), name='apply-rejected'),
    path('apply/list/all/', ApplyListView.as_view(), name='apply'),
    path('apply/<int:pk>/detail', ApplyDetailView.as_view(), name='apply-detail'),
    path('apply/new/', ApplyCreateView.as_view(), name='apply-create'),
    path('apply/<int:pk>/update/', ApplyUpdateView.as_view(), name='apply-update'),
    path('apply/<int:pk>/delete/', ApplyDeleteView.as_view(), name='apply-delete'),
    path('pdf/apply/list/', ApplicantListView.as_view(), name='pdf-apply-list'),
    path('apply/<int:pk>/reject/', RejectApplicant.as_view(), name='apply-reject'),

    path('thanks/', views.successful),
    path('test/', views.test_form, name='test')
]
