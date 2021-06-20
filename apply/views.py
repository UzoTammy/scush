from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Applicant
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.views.generic import (View,
                                  FormView,
                                  TemplateView,
                                  CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  )
from .forms import ApplicantForm, MyForm
import datetime
from django.urls import reverse_lazy


class ApplyListViewPending(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Applicant
    template_name = 'apply/applicant_list_pending.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['applicants_pending'] = self.get_queryset().filter(status=None).order_by('last_name')
        context['number_pending'] = context['applicants_pending']
        return context


class ApplyListViewEmployed(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Applicant
    template_name = 'apply/applicant_list_employed.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['applicants_employed'] = self.get_queryset().filter(status=True).order_by('last_name')
        context['number_pending'] = context['applicants_employed']
        return context


class ApplyListViewRejected(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Applicant
    template_name = 'apply/applicant_list_rejected.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rejected_applicants'] = self.get_queryset().filter(status=False).order_by('last_name')
        return context


class ApplyListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Applicant
    template_name = 'apply/applicant_list.html'
    context_object_name = 'all_applicants'
    ordering = 'last_name'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class ApplyDetailView(LoginRequiredMixin, DetailView):
    model = Applicant


def successful(request):
    return HttpResponse("""<h1 style="color:green;">Your form is submitted successfully!!!</h1>
    <a href="/">Return back to index page</a>""")


class WelcomeView(TemplateView):

    def get(self, request, *args, **kwargs):
        context = {
            'count': Applicant.objects.all().count,
        }
        return render(request, 'mails/welcome_applicant.html',
                      context)


class ApplyCreateView(CreateView):
    model = Applicant
    form_class = ApplicantForm
    success_url = '/thanks/'

    """This is to revalidate the form to ensure
    that the current logged in user is assigned as the creator"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        return context

    def form_valid(self, form):
        if form.instance.email:
            send_mail(subject='Application Submitted Successfully',
                      message="""We at Ozone F & L are pleased to receive your application.
                      We will get back to you on our decision. Thank you.""",
                      from_email=None,
                      html_message="",
                      recipient_list=[form.instance.email],
                      fail_silently=False)
        return super().form_valid(form)


class ApplyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Applicant
    form_class = ApplicantForm

    def test_func(self):
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    """This method runs only when all field data is cleaned and is necessary for
    the enhancement of the form"""
    def form_valid(self, form):
        form.instance.modified_date = datetime.datetime.now()
        return super().form_valid(form)

    def form_invalid(self, form):
        return super(ApplyUpdateView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        context['application_date'] = self.get_object().apply_date
        return context


class ApplyDeleteView(DeleteView):
    model = Applicant
    success_url = reverse_lazy('home')


def test_form(request):
    if request.method == 'POST':
        form = MyForm(request.POST)
        if form.is_valid():

            return render(request, 'apply/form_result.html', {'form': form})
    form = MyForm()
    return render(request, 'apply/my_name.html', {'form': form})



