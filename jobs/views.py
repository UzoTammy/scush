from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .models import JobPosting
from .forms import JobPostingForm


class HRDMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow access to HRD group members and superusers."""
    def test_func(self):
        u = self.request.user
        return u.is_superuser or u.groups.filter(name='HRD').exists()


# ── Public views ─────────────────────────────────────────────────────────────

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


# ── HR management views ───────────────────────────────────────────────────────

class JobManageView(HRDMixin, ListView):
    model = JobPosting
    template_name = 'jobs/job_manage.html'
    context_object_name = 'jobs'

    def get_context_data(self, **kwargs):
        import datetime
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
    if not (request.user.is_authenticated and (
        request.user.is_superuser or
        request.user.groups.filter(name='HRD').exists()
    )):
        return HttpResponseForbidden()

    job = get_object_or_404(JobPosting, pk=pk)
    job.status = (
        JobPosting.STATUS_CLOSED
        if job.status == JobPosting.STATUS_OPEN
        else JobPosting.STATUS_OPEN
    )
    job.save()
    return redirect('job-manage')
