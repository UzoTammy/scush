from django.urls import path
from . import views
from .views import *
from pdf.views import ApplicantListView

urlpatterns = [
    path('index/', ApplyIndexView.as_view(), name='apply-index'),
    path('home/', ApplyHomeView.as_view(), name='apply-home'),
    path('list/pending/', ApplyListViewPending.as_view(), name='apply-pending'),
    path('list/employed/', ApplyListViewEmployed.as_view(), name='apply-employed'),
    path('list/rejected/', ApplyListViewRejected.as_view(), name='apply-rejected'),
    path('list/all/', ApplyListView.as_view(), name='apply'),
    path('<int:pk>/detail/', ApplyDetailView.as_view(), name='apply-detail'),
    path('create/', ApplyCreateView.as_view(), name='apply-create'),
    path('<int:pk>/update/', ApplyUpdateView.as_view(), name='apply-update'),
    path('<int:pk>/delete/', ApplyDeleteView.as_view(), name='apply-delete'),
    
    path('apply/list/', ApplicantListView.as_view(), name='pdf-apply-list'),
    path('<int:pk>/reject/', RejectApplicant.as_view(), name='apply-reject'),

    path('thanks/', views.successful),
    path('test/', views.test_form, name='test')
]
