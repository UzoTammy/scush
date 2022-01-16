from django.shortcuts import render, reverse
from django.urls import reverse_lazy
from .models import CustomerProfile
from staff.models import Employee
from users.models import Profile
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
import ast
import os
import json
import secrets
import datetime
from ozone.mytools import CSVtoTuple
from django.shortcuts import render, redirect, reverse
from .forms import CustomerProfileForm, CustomerUpdateProfileForm


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


def generate_token():
    return secrets.token_hex(4)


def company(request):
    md = Employee.active.filter(position='MD')
    gsm = Employee.active.filter(position='GSM')
    scm = Employee.active.filter(position='SCM')
    hrm = Employee.active.filter(position='HRM')
    acct = Employee.active.filter(position='Accountant')
    mrk = Employee.active.filter(position='Marketing Manager')
    lyst = Employee.active.filter(position='Analyst')


    context = {
        'company': company,
        'members': md.union(gsm, scm, hrm, acct, mrk, lyst),
    }
    return render(request, 'customer/company.html', context)


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


class AboutView(TemplateView):
    template_name = 'customer/about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutView, self).get_context_data(**kwargs)
        context['title'] = 'About'
        return context


class HomeView(TemplateView):
    template_name = 'customer/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home'
        return context


class CustomerHomeView(TemplateView):
    template_name = 'customer/customer_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customers = CustomerProfile.objects.all()
        if customers.exists():
            context['customers'] = customers
            context['total_sales'] = customers.filter().aggregate(Sum('sales'))
            context['platinum_customers'] = customers.filter(category='Platinum')
            context['gold_customers'] = customers.filter(category='Gold')
            context['silver_customers'] = customers.filter(category='Silver')
            context['bronze_customers'] = customers.filter(category='Bronze')
            context['basic_customers'] = customers.filter(category='Basic')
            context['n_customers'] = customers.filter(category='')
            max_freq = customers.aggregate(Max('freq'))['freq__max']
            customer = customers.get(freq=max_freq)
            context['most_regular_customer'] = {
                'name': customer,
                'sales_value': customer.sales,
                'category': customer.category,
                'type': customer.type,
                
            }
            max_sales = customers.aggregate(Max('sales'))['sales__max']
            customer = customers.get(sales=max_sales)
            context['biggest_customer'] = {
                'name': customer,
                'sales_value': customer.sales,
                'category': customer.category,
                'type': customer.type
            }
        return context

class CustomerListView(LoginRequiredMixin, ListView):
    model = CustomerProfile
    template_name = 'customer/customer.html'
    context_object_name = 'customers'  # this replace the default object_list
    ordering = ['-date_created']

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['title'] = 'home'
        if self.get_queryset():
            context['total'] = self.get_queryset().filter(cluster='TRADE FAIR').count
            context['last_modified_object'] = self.get_queryset().latest('date_modified')
            context['last_time_modified'] = context['last_modified_object'].date_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomerProfile


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


class CustomerCreateView(LoginRequiredMixin, CreateView):
    # model = CustomerProfile
    template_name = 'customer/customerprofile_form.html'
    success_url = reverse_lazy('customer-list-all')
    form_class = CustomerProfileForm

    
    def form_valid(self, form):
        form.instance.category = categorize(form.instance.sales.amount)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        context['btn_text'] = 'Create'
        return context


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerProfile
    form_class = CustomerUpdateProfileForm

    def get(self, request, *args, **kwargs):
        obj = self.get_queryset().get(pk=kwargs['pk'])
        #get the string of section & convert to list
        # section = ast.literal_eval(obj.section)
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.date_modified = datetime.datetime.now()
        form.instance.category = categorize(form.instance.sales.amount)
        return super().form_valid(form)

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


class CSVCustomerView(View):
    pass


class RequestHome(TemplateView):
    template_name = 'customer/requests/request.html'