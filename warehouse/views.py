import datetime
import calendar
import decimal
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.views.generic import (View, TemplateView, ListView, CreateView, UpdateView, DetailView)
from .models import Stores, StoreLevy, Renewal, BankAccount
from .forms import BankAccountForm, StoreForm, StoreLevyForm, PayRentForm
from django.db.models import Sum
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from djmoney.money import Money

from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator


def next_year(date):
    year = date.year
    month = date.month
    day = date.day
    if calendar.isleap(year) and month == 2 and day == 29:
        month = 3
        day = 1
    year += 1
    return datetime.date(year, month, day)

class CacheControlMixin:
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class HomeView(LoginRequiredMixin, UserPassesTestMixin, CacheControlMixin, TemplateView):
    template_name = 'warehouse/home.html'
    rented_stores = Stores.active.exclude(owner='Self')
    stores = Stores.active.all()
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.stores.exists():
            total_capacity = self.stores.aggregate(Sum('capacity'))['capacity__sum']
            rented_capacity = self.rented_stores.aggregate(Sum('capacity'))['capacity__sum'] if self.rented_stores.exists() else 0.00
            owned_capacity = total_capacity - rented_capacity
            #percentage
            rented_percent = round(100*rented_capacity/total_capacity, 2) 
            owned_percent = round(100 - rented_percent, 2)

            #for rent amount
            rent_payable = round(self.rented_stores.aggregate(Sum('rent_amount'))['rent_amount__sum'], 2)
            rent_paid = round(rent_payable - self.rented_stores.filter(status=True).aggregate(Sum('rent_amount'))['rent_amount__sum'], 2)
            rent_unpaid = round(rent_payable - rent_paid, 2)
    
        context['rented_stores'] = {
            'currency': chr(8358),
            'today': datetime.date.today(),
            'all': self.rented_stores,
            'capacity': {
                'total': total_capacity,
                'rented': (rented_capacity, rented_percent),
                'owned': (owned_capacity, owned_percent),
            },
            'amount': {
                'payable': (rent_payable, self.rented_stores.count()),
                'paid': (rent_paid, self.rented_stores.filter(status=True).count()),
                'unpaid': (rent_unpaid, self.rented_stores.count() - self.rented_stores.filter(status=True).count())
            }
        }
        # context['N'] = chr(8358)
        # context['today'] = datetime.date.today()

        # context['owned_properties'] = Stores.active.filter(owner='Self')
        # context['rent_payable_per_annum'] = self.rented_stores.aggregate(total=Sum('rent_amount'))['total']
        # context['rent_amount_paid'] = self.rented_stores.filter(status=True).aggregate(total_paid=Sum('rent_amount'))['total_paid']
        # context['rent_amount_unpaid'] = self.rented_stores.filter(status=False).aggregate(total_paid=Sum('rent_amount'))['total_paid']

        # context['total_capacity'] = Stores.active.aggregate(total=Sum('capacity'))['total']
        # context['rented_capacity'] = self.rented_stores.aggregate(total=Sum('capacity'))['total']
        # context['owned_capacity'] = context['total_capacity'] - context['rented_capacity']
        # context['percent_rent'] = (100*context['owned_capacity']/context['total_capacity'], 100*context['rented_capacity']/context['total_capacity'])

        # context['store_types'] = (i[0] for i in Stores.TYPES)
        # context['usage'] = (i[0] for i in Stores.USAGE)
        # context['rent_amount_unpaid'] = context['rent_payable_per_annum'] - context['rent_amount_paid'] if self.renewed_stores.exists() else context['rent_payable_per_annum']
        
        # context['renewal_count'] = self.renewed_stores.count()

        # qs = Stores.active.all()
        # qs_total = qs.aggregate(total=Sum('rent_amount'))['total']
        # qsu = qs.filter(usage='Storage') | qs.filter(usage='Sell-out')
        # context['rent'] = {'office': qs.filter(usage='Office').aggregate(total=Sum('rent_amount'))['total'],
        #                     'apartment': qs.filter(usage='Apartment').aggregate(total=Sum('rent_amount'))['total'],
        #                     'storage': qsu.aggregate(total=Sum('rent_amount'))['total'],
        #                     }
        # office = 0 if context['rent']['office'] is None else 100*context['rent']['office']/qs_total
        # apartment = 0 if context['rent']['apartment'] is None else 100*context['rent']['apartment']/qs_total
        # storage = 0 if context['rent']['storage'] is None else 100 * context['rent']['storage'] / qs_total
        # context['rent_percentage'] = {'office': office,
        #                                 'apartment': apartment,
        #                                 'storage': storage}
        # context['stores'] = self.rented_stores.order_by('expiry_date')
        # context['owned_property_total'] = 30*context['owned_properties'].aggregate(Sum('rent_amount'))['rent_amount__sum']
        return context


class PayRentView(LoginRequiredMixin, TemplateView):
    template_name = 'warehouse/pay_rent_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PayRentForm()
        return context

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        store = get_object_or_404(Stores, pk=kwargs.get('pk'))
        form = PayRentForm(data=request.POST)

        if form.is_valid():
            # get the store, 
            store.status = True
            if store.expiry_date.month + int(request.POST['months']) > 12:
                month = store.expiry_date.month + int(request.POST['months']) - 12
                year = store.expiry_date.year + int(request.POST['years']) + 1
            else:
                month = store.expiry_date.month + int(request.POST['months'])
                year = store.expiry_date.year + int(request.POST['years'])
            store.expiry_date = datetime.date(year, month, store.expiry_date.day)
            store.save()
            
            renew = Renewal(
                store = store,
                date = datetime.datetime.strptime(request.POST['date_paid'], '%Y-%m-%d'),
                amount_paid = Money(decimal.Decimal(request.POST['amount_paid_0']), request.POST['amount_paid_1']),
            )
            renew.save()
            
            messages.success(request, 'Payment of Rent is successfully complete!!')
            return redirect('warehouse-home')
        
        context['form'] = form
            
        return render(request, self.template_name, context)

class StoresListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Stores
    template_name = 'warehouse/stores_list.html'
    ordering = ('store_type', 'name')

    context_object_name = 'stores'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)


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
    form_class = StoreForm
    
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
        messages.success(request, 'Changes Made Successfully !!!')
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


class BankAccountCreate(LoginRequiredMixin, CreateView):
    form_class = BankAccountForm
    template_name = 'warehouse/bankaccount_form.html'
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add'
        context['store'] = Stores.active.get(pk=self.kwargs['pk'])

        return context

    def form_valid(self, form):
        form.instance.store = Stores.active.get(pk=self.kwargs['pk'])
        try:
            return super().form_valid(form)
        except:
            messages.info(self.request, f'{form.instance.store} already have existing bank account !!!')
            return redirect('warehouse-list-all')   


class BankAccountUpdate(LoginRequiredMixin, UpdateView):
    model = BankAccount
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context


class BankAccountDetail(LoginRequiredMixin, DetailView):
    model = BankAccount
    

class DisableStoreAndAccount(LoginRequiredMixin, View):

    def get(self, request, **kwargs):
        store = Stores.active.get(pk=kwargs['pk'])
        bank_account = BankAccount.objects.get(store=store)
        store.disabled = True
        bank_account.disabled = True
        store.save()
        bank_account.save()
        messages.info(request, 'This Store and its Bank Account is disabled')
        return redirect('warehouse-detail', kwargs['pk'])


class StoreLevyCreateView(LoginRequiredMixin, CreateView):
    form_class = StoreLevyForm
    template_name = 'warehouse/storelevy_form.html'
    success_url = reverse_lazy('warehouse-home')

    def get(self, request: HttpRequest, *args: str, **kwargs: reverse_lazy) -> HttpResponse:
        return super().get(request, *args, **kwargs)


class StoreLevyListView(LoginRequiredMixin, ListView):
    model = StoreLevy

 
class StoreLevyUpdateView(LoginRequiredMixin, UpdateView):
    form_class = StoreLevyForm
    model = StoreLevy
    template_name = 'warehouse/storelevy_form.html'
    success_url = reverse_lazy('store-levy-list')
    
    