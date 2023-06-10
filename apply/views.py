import datetime
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.template import loader
from .models import Applicant
from staff.models import Terminate, Employee
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.contrib import messages
from django.utils import timezone
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
from django.utils.safestring import mark_safe

class ApplyIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'apply/index.html'
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['pending_applicants'] = Applicant.pending.all().order_by('-apply_date')
        context['resigned_staff'] = Terminate.objects.filter(status=True).filter(termination_type='Resign').order_by('-date')
        return context


class ApplyHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'apply/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applicant = Applicant.objects.all()
        ages = list((datetime.date.today() - date).days//365 for date in applicant.values_list('birth_date', flat=True) )
        
        context['applicants'] = {
            'count': applicant.count(),
            'gender': {
                'female': applicant.filter(gender='FEMALE').count(),
                'male': applicant.filter(gender='MALE').count(),
            },
            'status': {
                "employed": applicant.filter(status=True).count(), 
                "pending": applicant.filter(status=None).count(), 
                "rejected": applicant.filter(status=False).count()
            },
            'marital_status': {
                'married': applicant.filter(marital_status='MARRIED').count(),
                'single': applicant.filter(marital_status='SINGLE').count()
            },
            'stature': {
                'less_than_18': len(tuple(age for age in ages if age < 18)),
                'between_18_and_25': len(tuple(age for age in ages if 18 < age <= 25)),
                'above_25': len(tuple(age for age in ages if age > 25))
            },
        }
        
        context['this_year'] = str(datetime.date.today().year)
        applicant = applicant.filter(apply_date__year=datetime.date.today().year)
        ages = list((datetime.date.today() - date).days//365 for date in applicant.values_list('birth_date', flat=True) )
        
        context['this_year_applicants'] = {
            'count': applicant.count(),
            'gender': {
                'female': applicant.filter(gender='FEMALE').count(),
                'male': applicant.filter(gender='MALE').count(),
            },
            'status': {
                "employed": applicant.filter(status=True).count(), 
                "pending": applicant.filter(status=None).count(), 
                "rejected": applicant.filter(status=False).count()
            },
            'marital_status': {
                'married': applicant.filter(marital_status='MARRIED').count(),
                'single': applicant.filter(marital_status='SINGLE').count()
            },
            'stature': {
                'less_than_18': len(tuple(age for age in ages if age < 18)),
                'between_18_and_25': len(tuple(age for age in ages if 18 < age <= 25)),
                'above_25': len(tuple(age for age in ages if age > 25))
            }
        }
        return context


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
        context['year'] = str(datetime.datetime.today().year - 1)
        return context


class ApplyListViewEmployed(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Applicant
    template_name = 'apply/applicant_list_employed.html'
    context_object_name = 'objects'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    # def get_queryset(self):
    #     return super().get_queryset()
    
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
    queryset = Applicant.objects.all()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        employees_apply_id = Employee.objects.values_list('staff__pk', flat=True).distinct()
        context['status'] = True if self.kwargs['pk'] in employees_apply_id else False
            
        return context

    def post(self, request, **kwargs):
        
        # Employee database needs to change status to true
        employee = Employee.objects.get(staff__pk=self.kwargs['pk'])
        employee.status = True
        try:
            employee.basic_salary = 0.4 * float(self.request.POST['salary'])
            employee.allowance = 0.6 * float(self.request.POST['salary'])

            # Terminated database object change status
            terminated_employee = Terminate.objects.get(staff__staff__pk=self.kwargs['pk'])
            terminated_employee.status = False
            terminated_employee.save()
        except ValueError as varErr:
            messages.error(request, mark_safe(
                '<h6 id="flashElement" class="flash text-danger">&#x26A0; No value entered or you entered invalid value</h6>'
                )
            )
            return super().get(self, request, **kwargs)
        
        messages.success(request, mark_safe(
            f'<h6 class="text-success">{employee} successfully re-engaged &#10004;</h6>'))
        employee.save()
        return super().get(self, request, **kwargs)  

class ApplyCreateView(CreateView):
    """No login required and no restriction on user's needed, making it available
    to the public.
    """
    form_class = ApplicantForm
    template_name = 'apply/applicant_form.html'
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        return context

    def form_valid(self, form):
        hr_email = 'uzo.nwokoro@ozonefl.com'
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
    queryset = Applicant.objects.all()
    form_class = ApplicantForm

    def test_func(self):
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    """This method runs only when all field data is cleaned and is necessary for
    the enhancement of the form"""
    def form_valid(self, form):
        form.instance.modified_date = timezone.now()
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



