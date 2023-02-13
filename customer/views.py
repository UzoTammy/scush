import os
import csv
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.db.models import F, Sum
from django.core.mail import send_mail
from django.contrib import messages
from .models import Profile as CustomerProfile, CustomerCredit
from .forms import CustomerProfileForm, CustomerCreditForm, ChangeCreditValueForm
from trade.models import BalanceSheet
from users.models import Profile as UserProfile
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  TemplateView)


class CustomerHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/customer_home.html'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customers = CustomerProfile.objects.all()
        
        if customers.exists():
            qs = customers.filter(active=True)
            context['customers'] = customers
            context['active_customers'] = customers.filter(active=True)
            context['inactive_customers'] = customers.filter(active=False)
            context['lagos_customers'] = qs.filter(region='LOS')
            context['outside_lagos_customers'] = qs.filter(region='OLS')
            context['diaspora_customers'] = qs.filter(region='DSP')
            context['badagry_qs'] = qs.filter(cluster='BAD')
            context['barracks_qs'] = qs.filter(cluster='BAR')
            context['festac_qs'] = qs.filter(cluster='FES')
            context['lagos_island_qs'] = qs.filter(cluster='LIS')
            context['okoko_qs'] = qs.filter(cluster='OKO')
            context['omonile_qs'] = qs.filter(cluster='OMO')
            context['satellite_qs'] = qs.filter(cluster='SAT')
            context['trade_fair_qs'] = qs.filter(cluster='TRF')

            # This is classification
            qs_list = CustomerProfile.objects.values_list('classification', flat=True).distinct() #qs_list
            classes = {
                'OWP': '1-Way', 'ALL': 'All', 'RTW': 'Ret+Wine', 'WIN': 'Wine',
                'OWW': '1-Way+Wine', 'ROW':'Ret+1-Way', 'RTN': 'Returnable'
            }
            result = [(klass, qs.filter(classification=klass)) for klass in qs_list] # list of querysets
            classifications = [
                {'name': classes.get(topple[0]), 'count': topple[1].count} 
            for topple in result
            ]
            
            context['classes'] = classifications
        return context

    def post(self, request, **kwargs):
        
        if request.FILES:
            myfile = request.FILES['fileName']
            directory_path = os.path.dirname(__file__)
            fs = FileSystemStorage(location=os.path.join(directory_path, 'profile'))
            
            # remove all files and folders in fs.location
            if not fs.exists(fs.location):
                os.makedirs(fs.location)

            for file in fs.listdir('')[1]:
                path_file = os.path.join(fs.location, file)
                if os.path.exists(path_file):
                    os.remove(path_file)
            
            # # save the file into the file system
            filename = fs.save(myfile.name, myfile)
            messages.info(request, f'{filename} uploaded successfully')
        return super().get(request, **kwargs)

class CustomerListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomerProfile
    ordering = ['-pk']

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False
    
    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['title'] = 'home'
        if self.get_queryset():
            qs = self.get_queryset().filter(active=True)
            if self.kwargs['select'] == 'active':
                context['customers'] = self.get_queryset().filter(active=True)
                the_list = 'Active'
            elif self.kwargs['select'] == 'inactive':
                context['customers'] = self.get_queryset().filter(active=False)
                the_list = 'Deactivated'
            elif self.kwargs['select'] == 'lagos':
                context['customers'] = qs.filter(region='LOS')
                the_list = 'Lagos'
            elif self.kwargs['select'] == 'diaspora':
                context['customers'] = qs.filter(region='DSP')
                the_list = 'Diaspora'
            elif self.kwargs['select'] == 'outside_lagos':
                context['customers'] = qs.filter(region='OLS')
                the_list = 'Outside Lagos'
            else:
                context['customers'] = self.get_queryset()
                the_list = 'All'
        context['the_list'] = the_list
        return context

class CustomerClusterView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/profile_list.html'
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = CustomerProfile.objects.filter(active=True)
        clusters = {
            'badagry': 'BAD','barracks': 'BAR', 'lagos-island':'LIS', 'festac': 'FES', 
            'okoko': 'OKO', 'omonile': 'OMO','satellite': 'SAT', 'trade-fair': 'TRF'
        }
        context['customers'] = qs.filter(cluster=clusters.get(kwargs['cluster']))
        context['the_list'] = kwargs['cluster']
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomerProfile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = CustomerCredit.objects.filter(customerID=self.kwargs['pk'])
        if qs.exists():
            context['credit_value'] = (qs[0].current_credit, qs[0].credit_limit)
            context['has_credit'] = True
        else:
            context['has_credit'] = False
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    form_class = CustomerProfileForm
    template_name = 'customer/profile_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        context['btn_text'] = 'Create'
        return context

    def form_valid(self, form):
        if form.instance.contact_person == None:
            form.instance.contact_person = 'same as owner'
        if form.instance.contact_person.lower() == 'same as owner':
            form.instance.contact_person = f'{form.instance.business_owner.split()[0]}//{form.instance.mobile}'
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerProfile
    form_class = CustomerProfileForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        context['btn_text'] = 'Update'
        return context

    def form_valid(self, form):
        if form.instance.contact_person == None:
            form.instance.contact_person = 'same as owner'
        if form.instance.contact_person.lower() == 'same as owner':
            form.instance.contact_person = f'{form.instance.business_owner.split()[0]}//{form.instance.mobile}'
        return super().form_valid(form)

class CustomerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomerProfile
    success_url = reverse_lazy('customer-home')  # '/','/index/'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False

class RequestHome(LoginRequiredMixin, TemplateView):
    template_name = 'customer/requests/request.html'

class CustomerHelpView(TemplateView):
    template_name = 'customer/customer_help.html'

class CustomerProfileCSVView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/CSV/profile_list.html'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # with open()
        dirname = os.path.join(os.path.dirname(__file__), 'profile')
        filename = os.listdir(dirname)[0]
        file_path = os.path.join(dirname, filename)
        with open(file_path, 'r') as rf:
            content = csv.reader(rf)
            
            header = next(content)
            body = tuple(data for data in content if data[0] != '' or data[1] != '')
                
        context['header'] = header  
        context['body'] = body
        context['file_path'] = file_path
        context['dataset'] = CustomerProfile.objects.all()
        return context
    
    def post(self, request, **kwargs):
        data = self.get_context_data(**kwargs)['body']
        for record in data:
            if record[9].lower() == 'same as owner' or record[9] == '':
                record[9] = f'{record[1].split()[0]}//{record[5]}' 
            obj, created = CustomerProfile.objects.update_or_create(
                mobile = record[5],
                defaults={
                    'business_name': record[0],
                    'business_owner': record[1],
                    'address': record[2],
                    'cluster': record[3],
                    'region': record[4],
                    'second_mobile': record[6],
                    'email': record[7],
                    'classification': record[8],
                    'contact_person': record[9]
                }
            )
        messages.info(request, f'{CustomerProfile.objects.count()} records now in customer profile')    
        return super().get(request, **kwargs)

# Credits Record
class CustomerCreditListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomerCredit
    template_name = 'customer/credit/customercredit_list.html'
    ordering = ('isPermanent', '-current_credit')
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False

    def get_queryset(self):
        qs = super().get_queryset().filter(status=True).annotate(headroom=F('credit_limit') - F('current_credit'))
        return qs

    def get_context_data(self, **kwargs):
        context = super(CustomerCreditListView, self).get_context_data(**kwargs)
        capital = BalanceSheet.objects.last().capital
        total_credit = self.get_queryset().aggregate(Sum('current_credit'))['current_credit__sum']
        context['total_credit_value'] = total_credit
        context['capital_risk_factor'] = round(100*total_credit/capital.amount, 2)
        return context
    
    def post(self, request, **kwargs):
        if 'status' in request.POST:
            customer_status = request.POST['status']
            customer_status = customer_status.split('-')
            customer_id = int(customer_status[1])
            status = customer_status[0]
            status = False if status == 'disable' else None
            customer = get_object_or_404(CustomerCredit, pk=customer_id)
            customer.status = status
            customer.save()
            return self.get(request, **kwargs)

        send_mail(
            subject='Credit Limit Report', 
            message="",
            html_message="Credit Limit has been updated. <br> <a href='https://www.scush.com.ng/customer/credit/view/'>Click Here to view</a>",
            from_email='',
            recipient_list=['uzo.nwokoro@ozonefl.com'],
            fail_silently=True
            
            )
        messages.info(request, "Credit Limit email alert has been sent successfully!!!")
        return self.get(request, **kwargs)

class BlackListCreditListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomerCredit
    template_name = 'customer/credit/blacklisted_list.html'
    ordering = ('isPermanent', '-current_credit')
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False

    def get_queryset(self):
        qs = super().get_queryset().filter(status=None)
        return qs

class DisabledListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomerCredit
    template_name = 'customer/credit/disabled_list.html'
    ordering = ('isPermanent', '-current_credit')
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False

    def get_queryset(self):
        qs = super().get_queryset().filter(status=False)
        return qs

    def post(self, request, **kwargs):
        customer_id = request.POST['customer']
        customer = CustomerCredit.objects.get(pk=customer_id)
        customer.status = True
        customer.save()
        messages.info(request, f'{customer} is activated and moved successfully!!!')
        return self.get(request, **kwargs)


class CustomerCreditCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    # model = CustomerCredit
    form_class = CustomerCreditForm
    template_name = 'customer/credit/customercredit_form.html'
    
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def get_success_url(self) -> str:
        return reverse_lazy('customer-detail', kwargs={'pk': self.kwargs['code']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = get_object_or_404(CustomerProfile, pk=self.kwargs['code'])
        context['approver'] = self.request.user.profile.staff
        return context
    

    def form_valid(self, form):
        form.instance.customerID = get_object_or_404(CustomerProfile, pk=self.kwargs['code'])
        form.instance.approved_by = get_object_or_404(UserProfile, pk=self.request.user.pk)
        return super().form_valid(form)

class CustomerCreditUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomerCredit
    fields = "__all__"
    template_name = 'customer/credit/customercredit_form.html'
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def get_success_url(self) -> str:
        return reverse_lazy('customer-credit-list')

class CustomerChangeCreditValueView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomerCredit
    template_name = 'customer/credit/changecreditvalue.html'
    form_class = ChangeCreditValueForm

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        return False

    def get_success_url(self) -> str:
        return reverse_lazy('customer-credit-list')
