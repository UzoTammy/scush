import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View

from .models import JobPosting, JobApplication, Guarantor
from .forms import (
    JobPostingForm, ApplicationInitForm, ApplicantForm,
    GuarantorForm, HRNotesForm,
)


class HRDMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow access to HRD group members and superusers."""
    def test_func(self):
        u = self.request.user
        return u.is_superuser or u.groups.filter(name='HRD').exists()


def _is_hrd(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='HRD').exists()
    )


# ── Public views ──────────────────────────────────────────────────────────────

class JobListView(ListView):
    model = JobPosting
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'

    def get_queryset(self):
        return JobPosting.objects.filter(status=JobPosting.STATUS_OPEN)


class JobDetailView(DetailView):
    model = JobPosting
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'


# ── HR: Job posting management ────────────────────────────────────────────────

class JobManageView(HRDMixin, ListView):
    model = JobPosting
    template_name = 'jobs/job_manage.html'
    context_object_name = 'jobs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = datetime.date.today()
        return context


class JobCreateView(HRDMixin, CreateView):
    model = JobPosting
    form_class = JobPostingForm
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('job-manage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Job Posting'
        return context


class JobUpdateView(HRDMixin, UpdateView):
    model = JobPosting
    form_class = JobPostingForm
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('job-manage')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit — {self.object.title}'
        return context


def job_toggle_status(request, pk):
    """Toggle a posting between Open and Closed."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()
    job = get_object_or_404(JobPosting, pk=pk)
    job.status = (
        JobPosting.STATUS_CLOSED
        if job.status == JobPosting.STATUS_OPEN
        else JobPosting.STATUS_OPEN
    )
    job.save()
    return redirect('job-manage')


# ── HR: Application management ────────────────────────────────────────────────

class ApplicationListView(HRDMixin, ListView):
    model = JobApplication
    template_name = 'jobs/application_list.html'
    context_object_name = 'applications'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total']     = qs.count()
        context['pending']   = qs.filter(status=JobApplication.STATUS_PENDING).count()
        context['submitted'] = qs.filter(status=JobApplication.STATUS_SUBMITTED).count()
        context['interview'] = qs.filter(status=JobApplication.STATUS_INTERVIEW).count()
        context['employed']  = qs.filter(status=JobApplication.STATUS_EMPLOYED).count()
        context['rejected']  = qs.filter(status=JobApplication.STATUS_REJECTED).count()
        return context


class ApplicationInitView(HRDMixin, CreateView):
    """HR creates an application record and receives the applicant token link."""
    model = JobApplication
    form_class = ApplicationInitForm
    template_name = 'jobs/application_init.html'

    def get_success_url(self):
        return reverse('app-detail', kwargs={'pk': self.object.pk})


class ApplicationDetailView(HRDMixin, View):
    template_name = 'jobs/application_detail.html'

    def get_application(self, pk):
        return get_object_or_404(JobApplication, pk=pk)

    def get(self, request, pk):
        app = self.get_application(pk)
        notes_form = HRNotesForm(instance=app)
        return render(request, self.template_name, {
            'app': app,
            'notes_form': notes_form,
            'applicant_url': request.build_absolute_uri(
                reverse('applicant-form', kwargs={'token': app.token})
            ),
            'guarantor_url': (
                request.build_absolute_uri(
                    reverse('guarantor-form', kwargs={'token': app.guarantor.token})
                ) if app.has_guarantor() else None
            ),
        })

    def post(self, request, pk):
        app = self.get_application(pk)
        notes_form = HRNotesForm(request.POST, instance=app)
        if notes_form.is_valid():
            notes_form.save()
            messages.success(request, 'Notes saved.')
        return redirect('app-detail', pk=pk)


def application_set_status(request, pk):
    """HR advances or rejects an application."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()
    if request.method != 'POST':
        return redirect('app-detail', pk=pk)

    app = get_object_or_404(JobApplication, pk=pk)
    new_status = request.POST.get('status')

    allowed_transitions = {
        JobApplication.STATUS_SUBMITTED: [
            JobApplication.STATUS_INTERVIEW,
            JobApplication.STATUS_REJECTED,
        ],
        JobApplication.STATUS_INTERVIEW: [
            JobApplication.STATUS_ACCEPTED,
            JobApplication.STATUS_REJECTED,
        ],
        JobApplication.STATUS_ACCEPTED: [
            JobApplication.STATUS_REJECTED,
        ],
    }

    valid = allowed_transitions.get(app.status, [])
    if new_status in valid:
        app.status = new_status
        app.save()
        messages.success(request, f'Application status updated to "{app.get_status_display()}".')
    else:
        messages.error(request, 'Invalid status transition.')

    return redirect('app-detail', pk=pk)


def guarantor_request(request, pk):
    """HR creates a Guarantor record (generating the LOI token link) for an accepted application."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()

    app = get_object_or_404(JobApplication, pk=pk, status=JobApplication.STATUS_ACCEPTED)

    if not app.has_guarantor():
        Guarantor.objects.create(application=app)
        messages.success(request, 'Guarantor link generated. Copy and send it to the applicant.')
    else:
        messages.info(request, 'A guarantor link already exists for this application.')

    return redirect('app-detail', pk=pk)


def guarantor_review(request, pk):
    """HR approves or rejects a submitted guarantor, completing the employment decision."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()
    if request.method != 'POST':
        return redirect('app-detail', pk=pk)

    app = get_object_or_404(JobApplication, pk=pk)
    if not app.has_guarantor() or not app.guarantor.is_submitted():
        messages.error(request, 'Guarantor form has not been submitted yet.')
        return redirect('app-detail', pk=pk)

    decision = request.POST.get('decision')
    if decision == 'approve':
        app.guarantor.approved = True
        app.guarantor.save()
        app.status = JobApplication.STATUS_EMPLOYED
        app.save()
        messages.success(request, f'{app.applicant_name} has been successfully employed.')
    elif decision == 'reject':
        app.guarantor.approved = False
        app.guarantor.save()
        app.status = JobApplication.STATUS_REJECTED
        app.save()
        messages.warning(request, 'Application rejected — guarantor requirements not met.')
    else:
        messages.error(request, 'Invalid decision.')

    return redirect('app-detail', pk=pk)


# ── Public: Applicant token form ──────────────────────────────────────────────

def applicant_form(request, token):
    app = get_object_or_404(JobApplication, token=token)

    if app.is_link_expired() and app.status == JobApplication.STATUS_PENDING:
        return render(request, 'jobs/link_expired.html', {'kind': 'application'})

    if app.status != JobApplication.STATUS_PENDING:
        return render(request, 'jobs/applicant_submitted.html', {'app': app, 'already': True})

    if request.method == 'POST':
        form = ApplicantForm(request.POST, instance=app)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status = JobApplication.STATUS_SUBMITTED
            updated.submitted_at = timezone.now()
            updated.save()
            return redirect('applicant-submitted', token=token)
    else:
        form = ApplicantForm(instance=app)

    return render(request, 'jobs/applicant_form.html', {'form': form, 'app': app})


def applicant_submitted(request, token):
    app = get_object_or_404(JobApplication, token=token)
    return render(request, 'jobs/applicant_submitted.html', {'app': app, 'already': False})


# ── Public: Guarantor token form (Letter of Indemnity) ────────────────────────

def guarantor_form(request, token):
    guarantor = get_object_or_404(Guarantor, token=token)
    app = guarantor.application

    if guarantor.is_link_expired() and not guarantor.is_submitted():
        return render(request, 'jobs/link_expired.html', {'kind': 'guarantor'})

    if guarantor.is_submitted():
        return render(request, 'jobs/guarantor_submitted.html', {'guarantor': guarantor, 'already': True})

    if request.method == 'POST':
        form = GuarantorForm(request.POST, instance=guarantor)
        if form.is_valid():
            g = form.save(commit=False)
            g.submitted_at = timezone.now()
            g.save()
            return redirect('guarantor-submitted', token=token)
    else:
        form = GuarantorForm(instance=guarantor)

    return render(request, 'jobs/guarantor_form.html', {'form': form, 'app': app, 'guarantor': guarantor})


def guarantor_submitted(request, token):
    guarantor = get_object_or_404(Guarantor, token=token)
    return render(request, 'jobs/guarantor_submitted.html', {'guarantor': guarantor, 'already': False})


# ── HR: Link expiry management ────────────────────────────────────────────────

def extend_applicant_link(request, pk):
    """HR extends the applicant's form link by 14 more days."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()
    app = get_object_or_404(JobApplication, pk=pk)
    app.extend_link(days=14)
    messages.success(request, 'Applicant link extended by 14 days.')
    return redirect('app-detail', pk=pk)


def extend_guarantor_link(request, pk):
    """HR extends the guarantor's LOI link by 14 more days."""
    if not _is_hrd(request.user):
        return HttpResponseForbidden()
    app = get_object_or_404(JobApplication, pk=pk)
    if not app.has_guarantor():
        messages.error(request, 'No guarantor link exists for this application.')
        return redirect('app-detail', pk=pk)
    app.guarantor.extend_link(days=14)
    messages.success(request, 'Guarantor link extended by 14 days.')
    return redirect('app-detail', pk=pk)
