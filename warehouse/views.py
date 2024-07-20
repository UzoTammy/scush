import datetime
import decimal
from django.db.models.base import Model as Model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models.query import QuerySet
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import (View, TemplateView, ListView, CreateView, UpdateView, DetailView)

from djmoney.money import Money

from core.tools import QuerySum as Qsum
from .models import Stores, StoreLevy, Renewal, BankAccount
from .forms import BankAccountForm, StoreForm, StoreLevyForm, PayRentForm, RentRenewalUpdateForm
from .signals import signal_renew_store


def next_year(date):
    year = date.year
    month = date.month
    day = date.day
    if month == 2 and day == 29:
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
            total_capacity = Qsum.to_currency(self.stores, 'capacity')
            rented_capacity = Qsum.to_currency(self.rented_stores, 'capacity')
            owned_capacity = total_capacity - rented_capacity
            #percentage
            rented_percent = round(100*rented_capacity/total_capacity, 2) 
            owned_percent = round(100 - rented_percent, 2)

            #Rent payable and count
            rent_payable = Qsum.to_currency(self.rented_stores, 'rent_amount')
            count_payable = self.rented_stores.count()

            #prerequisite
            current_year = datetime.date.today().year
            #rent paid and count
            qs = Renewal.objects.filter(date__year=current_year)
            rent_paid = Qsum.to_currency(qs, 'amount_paid') #rent paid
            stores_in_renewal = qs.values_list('store__pk', flat=True).distinct() 
            count_paid = stores_in_renewal.count() #rent count
            
            #unpaid rent and count
            qs = self.rented_stores.filter(expiry_date__year__lte=current_year)
            rent_unpaid = Qsum.to_currency(qs, 'rent_amount') #rent unpaid
            count_unpaid = qs.count() #unpaid rent count
            
            #Levy payable and count
            payable_amount = Qsum.to_currency(self.stores, 'allocated_levy_amount')
            payable_count = self.stores.count()

            #levy paid amount and count
            qs = StoreLevy.objects.filter(payment_date__year=current_year)
            paid_amount = Qsum.to_currency(qs, 'amount_paid')
            stores_that_paid_levy = qs.values_list('store__pk', flat=True).distinct()
            paid_count = stores_that_paid_levy.count()

            #levy unpaid amount and count

            context['rented_stores'] = {
                
                'today': datetime.date.today(),
                'all': self.rented_stores.order_by('expiry_date'),
                'capacity': {
                    'total': total_capacity,
                    'rented': (rented_capacity, rented_percent),
                    'owned': (owned_capacity, owned_percent),
                },
                'amount': {
                    'payable': (rent_payable, count_payable),
                    'paid': (rent_paid, count_paid),
                    'unpaid': (rent_unpaid, count_unpaid)
                },
                'levy': {
                    'payable': (payable_amount, payable_count),
                    'paid': (paid_amount, paid_count),
                    'unpaid': (payable_amount - paid_amount, payable_count - paid_count),
                    # this unpaid can be made more accurate by looking at stores one-by-one
                    # take a store, get the levy at store's model, get the paid amount at storelevy model
                    # if they are equal report zero or report the difference. do this for every store
                    # sum the results to get the unpaid
                }
            }

            context['usage'] = {
                'number': {
                    'sell_out': self.stores.filter(usage='Sell-out').count(),
                    'storage': self.stores.filter(usage='Storage').count(),
                    'office': self.stores.filter(usage='Office').count(),
                    'apartment': self.stores.filter(usage='Apartment').count(),
                },
                'levy': {
                    'sell_out': Qsum.to_currency(self.stores.filter(usage='Sell-out'), 'allocated_levy_amount'),
                    'storage': Qsum.to_currency(self.stores.filter(usage='Storage'), 'allocated_levy_amount'),
                    'office': Qsum.to_currency(self.stores.filter(usage='Office'), 'allocated_levy_amount'),
                    'apartment': Qsum.to_currency(self.stores.filter(usage='Apartment'), 'allocated_levy_amount'),
                },
                'rent': {
                    'sell_out': Qsum.to_currency(self.stores.filter(usage='Sell-out'), 'rent_amount'),
                    'storage': Qsum.to_currency(self.stores.filter(usage='Storage'), 'rent_amount'),
                    'office': Qsum.to_currency(self.stores.filter(usage='Office'), 'rent_amount'),
                    'apartment': Qsum.to_currency(self.stores.filter(usage='Apartment'), 'rent_amount'),
                },

            }
        return context


class PayRentView(LoginRequiredMixin, TemplateView):
    template_name = 'warehouse/pay_rent_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PayRentForm()
        context['store'] = get_object_or_404(Stores, pk=self.kwargs.get('pk'))
        return context

    def post(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        store = context.get('store')

        form = PayRentForm(request.POST)

        if form.is_valid():
            # get the store, 
            renew = Renewal(
                store = store,
                date = datetime.datetime.strptime(request.POST['date_paid'], '%Y-%m-%d'),
                amount_paid = Money(decimal.Decimal(request.POST['amount_paid_0']), request.POST['amount_paid_1']),
            )
            renew.save()

            signal_renew_store.send(sender=None, instance=store, extra_data={'month': int(request.POST['months']), 'year': int(request.POST['years'])})
            
            messages.success(request, 'Payment of Rent is successfully complete!!')
            return redirect('store-rent-list')
        
        context['form'] = form
            
        return render(request, self.template_name, context)


class UpdateRentView(LoginRequiredMixin, TemplateView):
    template_name = 'warehouse/pay_rent_form.html'

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        renew_obj = get_object_or_404(Renewal, pk=self.kwargs.get('pk'))
        context['form'] = RentRenewalUpdateForm(instance=renew_obj)
        context['update'] = True
        context['renew_obj'] = renew_obj
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = RentRenewalUpdateForm(request.POST, instance=context.get('renew_obj'))
        if form.is_valid():
            form.instance.store = context.get('renew_obj').store
            form.instance.date = datetime.datetime.strptime(request.POST['date'], '%Y-%m-%d')
            form.instance.amount_paid = Money(decimal.Decimal(request.POST['amount_paid_0']), request.POST['amount_paid_1'])
            form.save()
            signal_renew_store.send(sender=None, instance=form.instance.store, extra_data={'month': int(request.POST['month']), 'year': int(request.POST['year'])})
            messages.success(request, 'Update of Rent is successful!!')
            return redirect('store-rent-list')
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
        current_year = datetime.date.today().year
        context['renew_list'] = Renewal.objects.filter(date__year=current_year).filter(store__pk=self.kwargs.get('pk'))
        
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


class StoreLevyListView(LoginRequiredMixin, ListView):
    model = StoreLevy

 
class StoreLevyUpdateView(LoginRequiredMixin, UpdateView):
    form_class = StoreLevyForm
    model = StoreLevy
    template_name = 'warehouse/storelevy_form.html'
    success_url = reverse_lazy('store-levy-list')

class RentListView(LoginRequiredMixin, ListView):
    template_name = 'warehouse/storerent_list.html'
    model = Renewal
    
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(date__year=datetime.date.today().year).order_by('store')