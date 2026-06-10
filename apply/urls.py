from django.urls import path
from . import views
from .views import *
from pdf.views import ApplicantListView

urlpatterns = [
    path('index/', ApplyIndexView.as_view(), name='apply-index'),
    path('home/', ApplyHomeView.as_view(), name='apply-home'),
    path('list/all/', ApplyListView.as_view(), name='apply'),
    path('<int:pk>/detail/', ApplyDetailView.as_view(), name='apply-detail'),
    path('create/', ApplyCreateView.as_view(), name='apply-create'),
    path('<int:pk>/update/', ApplyUpdateView.as_view(), name='apply-update'),
    path('<int:pk>/delete/', ApplyDeleteView.as_view(), name='apply-delete'),
    
    path('apply/list/', ApplicantListView.as_view(), name='pdf-apply-list'),
    path('<int:pk>/reject/', RejectApplicant.as_view(), name='apply-reject'),
    path('<int:pk>/interview/', GrantInterview.as_view(), name='apply-interview'),
    path('<int:pk>/guarantor/download/', views.guarantor_form_pdf, name='guarantor-form-pdf'),
    path('<int:pk>/guarantor/upload/', views.upload_guarantor_doc, name='guarantor-doc-upload'),
    path('<int:pk>/guarantor/reupload/request/', views.request_guarantor_reupload, name='guarantor-reupload-request'),
    path('<int:pk>/guarantor/reupload/approve/', views.approve_guarantor_reupload, name='guarantor-reupload-approve'),

    path('thanks/', views.successful),
    path('test/', views.test_form, name='test'),

    # ── Email-invite application flow ─────────────────────────────────────────
    path('invite/', views.RequestInviteView.as_view(), name='apply-invite'),
    path('invited/', TemplateView.as_view(template_name='apply/invite_done.html'), name='apply-invited'),
    path('form/<uuid:token>/', views.PublicApplyView.as_view(), name='apply-form'),

    path('welcome/', views.WelcomeView.as_view(), name='welcome'),
]
