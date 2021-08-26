import datetime
import calendar
from django.urls import reverse_lazy
from django.views.generic import (View, TemplateView, ListView, CreateView, UpdateView, DetailView)
from .models import Stores, Renewal
from .form import StoreForm
from django.db.models import Sum
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def next_year(date):
    year = date.year
    month = date.month
    day = date.day
    if calendar.isleap(year) and month == 2 and day == 29:
        month = 3
        day = 1
    year += 1
    return datetime.date(year, month, day)


class HomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'warehouse/home.html'
    queryset = Stores.active.exclude(owner='Self')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.queryset.exists():
            context['properties'] = Stores.active.filter(owner='Self')
            context['N'] = chr(8358)
            context['today'] = datetime.date.today()
            context['store_types'] = (i[0] for i in Stores.TYPES)
            context['usage'] = (i[0] for i in Stores.USAGE)
            context['total_rent_payable_per_annum'] = self.queryset.aggregate(total=Sum('rent_amount'))['total']
            context['sellout_capacity'] = self.queryset.filter(usage='Sell-out').aggregate(total_sellout=Sum('capacity'))['total_sellout']
            context['storage_capacity'] = self.queryset.filter(usage='Storage').aggregate(total_storage=Sum('capacity'))['total_storage']
            context['rent_amount_paid'] = self.queryset.filter(status=True).aggregate(total_paid=Sum('rent_amount'))['total_paid']
            context['rent_amount_unpaid'] = self.queryset.filter(status=False).aggregate(total_unpaid=Sum('rent_amount'))['total_unpaid']
            context['quantity_rent'] = {'paid': self.queryset.filter(status=True).count(), 'unpaid': self.queryset.filter(status=False).count()}
            context['stores'] = self.queryset.order_by('expiry_date')
        return context


class StoresListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Stores
    template_name = 'warehouse/stores_list.html'
    context_object_name = 'stores'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class StoreHelpView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'warehouse/help.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class StoresDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Stores

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expiry_date'] = next_year(kwargs['object'].expiry_date)
        context['range'] = range(1, 12)
        return context


class StoresCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = StoreForm
    template_name = 'warehouse/stores_form.html'
    success_url = reverse_lazy('warehouse-home')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New'
        return context


class StoresUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Stores
    template_name = 'warehouse/stores_form.html'
    fields = ('name',
              'store_type',
              'usage',
              'owner',
              'address',
              'contact',
              'rent_amount',
              'capacity',
              'expiry_date')
    success_url = reverse_lazy('warehouse-home')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context


class PayRent(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Stores

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        qs = self.get_queryset().get(id=kwargs['pk'])
        period = int(request.POST['period'])
        the_unit = request.POST['unit']
        date = qs.expiry_date
        if the_unit == 'Year':
            factor = period
            for _ in range(period):
                date = next_year(date)
        else:
            factor = period/12
            num = date.month + period
            if num > 12:
                num -= 12
                year = date.year + 1
            else:
                year = date.year
            date = datetime.date(year, num, date.day)

        qs.expiry_date = date
        qs.save()

        # This session is to create renewal database
        renew = Renewal(store=qs,
                        date=datetime.date.today(),
                        amount_paid=qs.rent_amount*factor,
                        expiry_date=date)
        renew.save()

        # the message
        messages.success(request, f'Rent renewal saved successfully !!!')
        return redirect('warehouse-detail', pk=kwargs['pk'])
