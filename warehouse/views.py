import datetime
import calendar
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (View, TemplateView, ListView, CreateView, UpdateView, DetailView)
from .models import Stores, Renewal, BankAccount
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
    store_obj = Stores.active.exclude(owner='Self')
    payment_obj = Renewal.objects.filter(date__year=datetime.date.today().year)

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.store_obj.exists():
            for obj in self.store_obj:
                if obj.expiry_date >= datetime.date.today():
                    obj.status = False
                    obj.save()

            context['N'] = chr(8358)
            context['today'] = datetime.date.today()

            context['owned_properties'] = Stores.active.filter(owner='Self')

            context['total_rent_payable_per_annum'] = self.store_obj.aggregate(total=Sum('rent_amount'))['total']
            context['total_capacity'] = Stores.active.aggregate(total=Sum('capacity'))['total']
            context['rented_capacity'] = self.store_obj.aggregate(total=Sum('capacity'))['total']
            context['owned_capacity'] = context['total_capacity'] - context['rented_capacity']

            context['store_types'] = (i[0] for i in Stores.TYPES)
            context['usage'] = (i[0] for i in Stores.USAGE)
            context['rent_amount_paid'] = self.payment_obj.aggregate(total_paid=Sum('amount_paid'))['total_paid']
            context['rent_amount_unpaid'] = context['total_rent_payable_per_annum'] - context['rent_amount_paid'] if self.payment_obj.exists() else context['total_rent_payable_per_annum']
            context['renewal_count'] = self.payment_obj.count()

            qs = Stores.active.all()
            qs_total = qs.aggregate(total=Sum('rent_amount'))['total']
            qsu = qs.filter(usage='Storage') | qs.filter(usage='Sell-out')
            context['rent'] = {'office': qs.filter(usage='Office').aggregate(total=Sum('rent_amount'))['total'],
                               'apartment': qs.filter(usage='Apartment').aggregate(total=Sum('rent_amount'))['total'],
                               'storage': qsu.aggregate(total=Sum('rent_amount'))['total'],
                               }
            office = 0 if context['rent']['office'] is None else 100*context['rent']['office']/qs_total
            apartment = 0 if context['rent']['apartment'] is None else 100*context['rent']['apartment']/qs_total
            storage = 0 if context['rent']['storage'] is None else 100 * context['rent']['storage'] / qs_total
            context['rent_percentage'] = {'office': office,
                                          'apartment': apartment,
                                          'storage': storage}
            context['stores'] = self.store_obj.order_by('expiry_date')
            context['owned_property_total'] = 30*context['owned_properties'].aggregate(Sum('rent_amount'))['rent_amount__sum']
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

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(StoresListView, self).get_context_data(**kwargs)
        context['stores_bank'] = BankAccount.objects.all()
        return context


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
    # success_url = reverse_lazy('warehouse-home')

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
              'expiry_date',
              'status',
              'disabled')
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

        
    def post(self, request, *args, **kwargs):
        # the message
        messages.success(request, f'Changes Made Successfully !!!')
        return super().post(request, *args, **kwargs)

    
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
        if the_unit == 'Year':
            factor = period
            date = datetime.date(qs.expiry_date.year + period, qs.expiry_date.month, qs.expiry_date.day)
        else:
            factor = period/12
            num = qs.expiry_date.month + period
            if num > 12:
                num -= 12
                year = qs.expiry_date.year + 1
            else:
                year = qs.expiry_date.year
            date = datetime.date(year, num, qs.expiry_date.day)
        qs.expiry_date = date
        qs.status = True
        qs.save()

        # This session is to create renewal database
        renew = Renewal(store=qs,
                        date=datetime.date.today(),
                        amount_paid=qs.rent_amount*factor,
                        )
        renew.save()

        # the message
        messages.success(request, f'Rent renewal successfully !!!')

        return redirect('warehouse-detail', pk=kwargs['pk'])


class BankAccountCreate(CreateView):
    model = BankAccount
    success_url = reverse_lazy('warehouse-home')
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add'
        return context


class BankAccountUpdate(UpdateView):
    model = BankAccount
    success_url = reverse_lazy('warehouse-home')
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context