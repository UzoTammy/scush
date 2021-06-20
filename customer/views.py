from django.shortcuts import render, reverse
from django.urls import reverse_lazy
from .models import CustomerProfile
from users.models import Profile
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  View,
                                  TemplateView)
# from django.views.generic.base import T
from django.core.paginator import Paginator
from django.conf import settings
import os
import json
import secrets
import datetime
from ozone.mytools import CSVtoTuple
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.core.mail import send_mail
from django.template import loader


class CSVPart(View):

    def get(self, request):
        obj_list = CSVtoTuple(
            os.path.join(settings.BASE_DIR, 'customer/static/customers.csv')).csv_content(
            integer=(0,), decimal=(7,)
        )
        objects = list()

        for record in obj_list:
            month = 4
            year = 12
            factor = month/year

            def categorize(value):
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
            object['category'] = categorize(record[7])
            object['complete'] = False
            objects.append(object)

        context = {
            'objects': objects,
        }
        return render(request, 'customer/customer_db_csv.html', context)


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


with open(os.path.join(settings.BASE_DIR, 'customer/static/customer/company.json'), 'r') as rf:
    company = json.load(rf)

company['Core Values'] = company.get('Core Values').split(',')


def index(request):
    context = {
        'company': company,
    }
    return render(request, 'customer/index.html', context)


def home(request):
    the_path = 'customer/static/customer/secret.json'
    with open(os.path.join(settings.BASE_DIR, the_path), 'r') as rf:
        data = json.load(rf)
        token = data[0]['token']
    context = {
        'title': 'Home',
        'company': company,
        'token': token,
        'toke_url': (token,),
    }
    return render(request, 'customer/home.html', context)


def about(request):
    context = {
        'title': 'About',
    }
    return render(request, 'customer/about.html', context)


def company(request):
    context = {
        'company': company,
        'members': Profile.objects.all().exclude(id=1),
        'leader': Profile.objects.get(id=1)
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


class CustomerListView(LoginRequiredMixin, ListView):
    model = CustomerProfile
    template_name = 'customer/customer.html'
    context_object_name = 'customers'  # this replace the default object_list
    ordering = ['-date_created']

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['title'] = 'home'
        context['total'] = CustomerProfile.objects.filter(cluster='TRADE FAIR').count
        context['last_modified_object'] = self.get_queryset().latest('date_modified')
        context['last_time_modified'] = context['last_modified_object'].date_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomerProfile


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = CustomerProfile
    fields = ['business_name',
              'business_owner',
              'region',
              'cluster',
              'category',
              'mobile',
              'email',
              'address',
              ]

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        context['btn_text'] = 'Create'
        return context


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerProfile
    fields = ['business_name',
              'business_owner',
              'region',
              'cluster',
              'category',
              'mobile',
              'email',
              'address',
              ]

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.date_modified = datetime.datetime.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        context['btn_text'] = 'Update'
        return context


class CustomerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomerProfile
    success_url = reverse_lazy('customer-list')  # '/','/index/'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False


# class CSVToModel(CreateView):
#     model = CustomerProfile
#     fields = '__all__'
#
#     def form_invalid(self, form):
#         # form.instance.xx = self.
#         return super().form_invalid(form)