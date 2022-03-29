import datetime
import logging
from pathlib import Path
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.template import loader
from .models import Applicant
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.contrib import messages
from django.views.generic import (View,
                                  TemplateView,
                                  CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  )
from .forms import ApplicantForm, MyForm
from django.urls import reverse_lazy, reverse


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s:%(levelname)s %(asctime)s %(message)s', datefmt='%d-%b-%Y %I:%M %p')
path = Path(__file__).resolve().parent

file_handler = logging.FileHandler(path / 'log' / 'views.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


"""This view is completely class based views. It starts with listing all pending
applicants. From here, employed and rejected applicants can be listed with 
ApplyListViewEmployed and ApplyListViewRejected classes respectively.
Also, all applicants are listed with ApplyListView class.
Since CBVs allow for list, detail, update and create and even delete,
they are all utilized in this model to manage the data. However, more functiona
are applied."""

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
        context['title'] = 'Applicants-pending'
        context['applicants_pending'] = self.get_queryset().filter(status=None).order_by('last_name')
        context['number_pending'] = context['applicants_pending']

        context['applicants'] = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year - 1).count()
        context['employed'] = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year - 1, status=True).count()
        context['rejected'] = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year - 1, status=False).count()
        context['pending'] = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year - 1, status=None).count()
        
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
        context['title'] = 'Applicants-employed'
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


class ApplyCreateView(CreateView):
    """No login required and no restriction on user's needed, making it available
    to the public.
    """
    model = Applicant
    form_class = ApplicantForm
    
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        return context

    def form_valid(self, form):
        hr_email = 'dickson.abanum@ozonefl.com'
        context = {
            'first_name': form.instance.first_name,
            'second_name': form.instance.second_name,
            'last_name': form.instance.last_name,
            'gender': form.instance.gender,
            'marital_status': form.instance.marital_status,
            'qualification': form.instance.qualification,
            'date_of_birth': form.instance.birth_date,
            'course': form.instance.course,
            'mobile': form.instance.mobile,
            'email': form.instance.email,
            'address': form.instance.address,
            'header': f'Your application received successfully'
        }
        if form.instance.email:
            email = EmailMessage(
                subject='Application for a job at Ozone',
                body=loader.render_to_string('mail/apply_for_job.html', context),
                from_email='',
                to=[form.instance.email],
                cc=[hr_email]
            )
            email.content_subtype = 'html'
            email.send(fail_silently=True)

        # return HttpResponse('testing')
        return super().form_valid(form)


class RejectApplicant(View):

    def get(self, request, *args, **kwargs):
        applicant = get_object_or_404(Applicant, id=kwargs['pk'])
        if request.GET['result'] == 'Yes':
            applicant.status = False
            applicant.save()
            messages.info(request, f'{applicant} rejected successfully!!!')
        return redirect(reverse('apply-detail', kwargs={'pk': applicant.id}))


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


class WelcomeView(TemplateView):

    def get(self, request, *args, **kwargs):
        context = {
            'count': Applicant.objects.all().count,
        }
        return render(request, 'mails/welcome_applicant.html',
                      context)


def successful(request):
    return HttpResponse("""<h1 style="color:green;">Your form is submitted successfully!!!</h1>
    <a href="/">Return back to index page</a>""")


def test_form(request):
    if request.method == 'POST':
        form = MyForm(request.POST)
        if form.is_valid():

            return render(request, 'apply/form_result.html', {'form': form})
    form = MyForm()
    return render(request, 'apply/my_name.html', {'form': form})



