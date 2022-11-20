import os
import secrets
import datetime
from django.shortcuts import render
from django.urls import reverse_lazy
from .models import CustomerProfile
from django.db.models import F, Sum, Max
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  View,
                                  TemplateView)
from django.conf import settings
from ozone.mytools import CSVtoTuple
# from .forms import CustomerProfileForm, CustomerUpdateProfileForm


def generate_token():
    return secrets.token_hex(4)

def permit(request):
    result = ''
    if request.method == 'POST':
        if request.POST.get('token') == '123456':
            result = 'passed'
        #     generate another token to replace
        else:
            result = 'failed'
    else:
        pass

    context = {'result': result}
    return render(request, 'customer/permit.html', context)

def categorize(sales):
    if sales >= 100e6:
        result = 'Platinum'
    elif sales >= 50e6:
        result = 'Gold'
    elif sales >= 10e6:
        result = 'Silver' 
    elif sales >= 5e6:
        result = 'Bronze'
    else:
        result = 'Basic'
    return result


class CSVPart(TemplateView):
    queryset = CustomerProfile.objects.all()
    ordering = '-pk'
    template_name = 'customer/customer_db_csv.html'

    def categorize(self, value, factor=4/12):
        if value >= 100e6 * factor:
            return 'Platinum'
        elif 70e6 * factor <= value < 100e6 * factor:
            return 'Gold'
        elif 50e6 * factor <= value < 70e6 * factor:
            return 'Silver'
        elif 30e6 * factor <= value < 50e6 * factor:
            return 'Bronze'
        elif 10e6 * factor <= value < 30e6 * factor:
            return 'Basic'
        elif 1e6 * factor <= value < 10e6 * factor:
            return 'Normal'
        elif 0 < value < 1e6 * factor:
            return 'NYC'
        elif value == 0:
            return 'Inactive'

    def get(self, request, **kwargs):
        obj_list = CSVtoTuple(
            os.path.join(settings.BASE_DIR, 'customer/static/customers.csv')).csv_content(integer=(0,), decimal=(7,))
        objects = list()

        for record in obj_list:

            object = dict()
            object['id'] = record[0]
            object['business'] = record[2]
            object['owner'] = record[1]
            object['cluster'] = record[6]
            object['address'] = record[3]
            object['mobile'] = record[4]
            object['email'] = record[5]
            object['type'] = record[8]
            object['sales'] = record[7]
            object['freq'] = 'NA'
            object['category'] = self.categorize(record[7])
            object['complete'] = False
            objects.append(object)

        context = {
            'title': 'Customer CSV Data List',
            'objects': objects,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        context = {}
        my_dict = request.POST.copy()
        my_dict.pop('csrfmiddlewaretoken')

        if my_dict:
            for key, value in my_dict.items():
                value = value.split('|')
                value[5] = '' if value[5] == 'Nil' else value[5]
                value[8] = 0 if value[8] == 'NA' or value[8] == '' else value[8]
                qs = CustomerProfile(
                    business_name=value[0],
                    business_owner=value[1],
                    cluster=value[2],
                    address=value[3],
                    mobile=value[4],
                    email=value[5],
                    sales=float(value[7].replace(',', '')),
                    category=self.categorize(float(value[7].replace(',', ''))),
                    freq=int(value[8]),
                )

                if self.queryset.filter(business_name=value[0]).exists():
                    msg = 'Record already exist'
                    context['message'] = msg
                    return render(request, self.template_name, context)
                else:
                    qs.save()

            objects = list()
            for record in self.queryset.order_by('-pk'):
                object = dict()
                object['id'] = record.id
                object['business'] = record.business_name
                object['owner'] = record.business_owner
                object['cluster'] = record.cluster
                object['address'] = record.address
                object['mobile'] = record.mobile
                object['email'] = record.email
                object['type'] = record.type
                object['sales'] = record.sales
                object['freq'] = record.freq
                object['category'] = record.category
                objects.append(object)
            context['objects'] = objects
            context['title'] = "Customer's Database Record"
        else:
            msg = 'No Record added'
            context['message'] = msg
        return render(request, self.template_name, context)


class CSVCustomerDetail(View):

    def get(self, request, id):
        obj_list = CSVtoTuple(
            os.path.join(settings.BASE_DIR, 'customer/static/customers.csv')).csv_content(
            integer=(0,), decimal=(7,)
        )
        data = obj_list[id-1]
        objects = dict()
        objects['id'] = data[0]
        objects['business'] = data[2]
        objects['owner'] = data[1]
        objects['address'] = data[3]
        objects['mobile'] = data[4]
        objects['region'] = 'Lagos'
        objects['email'] = data[5]
        objects['cluster'] = data[6]
        objects['sales'] = data[7]
        objects['type'] = data[8]
        objects['category'] = data[9]

        context = {
            'object': objects
        }
        return render(request, 'customer/CSV/customer_csv_detail.html', context)


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
                {'name': classes.get(topple[0]), 'count': topple[1].count, 'sales': 20} 
            for topple in result
            ]
            
            context['classes'] = classifications
        return context


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
            elif self.kwargs['select'] == 'inactive':
                context['customers'] = self.get_queryset().filter(active=False)
            elif self.kwargs['select'] == 'lagos':
                context['customers'] = qs.filter(region='LOS')
            elif self.kwargs['select'] == 'diaspora':
                context['customers'] = qs.filter(region='DSP')
            elif self.kwargs['select'] == 'outside_lagos':
                context['customers'] = qs.filter(region='OLS')
            else:
                context['customers'] = self.get_queryset()

        return context


class CustomerClusterView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/customer_cluster.html'
    
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

        context['cluster'] = qs.filter(cluster=clusters.get(kwargs['cluster']))
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomerProfile


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = CustomerProfile
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        context['btn_text'] = 'Create'
        return context


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerProfile
    fields = "__all__"
    # form_class = CustomerUpdateProfileForm

    def get(self, request, *args, **kwargs):
        obj = self.get_queryset().get(pk=kwargs['pk'])
        #get the string of section & convert to list
        # section = ast.literal_eval(obj.section)
        return super().get(request, *args, **kwargs)
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        context['btn_text'] = 'Update'
        return context


class CustomerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomerProfile
    success_url = reverse_lazy('customer-list-all')  # '/','/index/'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False


class RequestHome(LoginRequiredMixin, TemplateView):
    template_name = 'customer/requests/request.html'


class CustomerHelpView(TemplateView):
    template_name = 'customer/customer_help.html'