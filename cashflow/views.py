import datetime
from typing import Any
from django.forms import BaseModelForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from djmoney.money import Money

from .forms import (BankAccountForm, CashCollectForm, CashDepositForm, DisburseForm, 
                    CurrentBalanceUpdateForm, RequestToWithdrawForm, InterbankTransferForm,
                    DisableAccountForm, ApproveWithdrawalForm, AdministerWithdrawalForm)
from .models import BankAccount, CashDepot, Withdrawal
from core.tools import QuerySum
# Create your views here.

class BankAccountCreateView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = BankAccountForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'New Bank Account Form'
        return context

class CashflowHomeView(LoginRequiredMixin, FormView):
    # model = BankAccount
    template_name = 'cashflow/home.html'
    form_class = CurrentBalanceUpdateForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['object_list'] = BankAccount.objects.all()
        context['cash'] = CashDepot.objects.latest('date').balance
        context['date'] = CashDepot.objects.latest('date').date
        context['current_bank_balance_total'] = QuerySum.to_currency(BankAccount.objects.filter(status=True), 'current_balance')
        context['pending_withdrawals'] = Withdrawal.objects.exclude(stage=-1).exclude(stage=2)
        return context
    
    def form_valid(self, form: Any) -> HttpResponse:
        account_number = self.request.POST['account_number']
        bank_account = BankAccount.objects.get(pk=account_number)
        if 'action' in self.request.POST and self.request.POST['action'] == 'current_balance':
            bank_account.current_balance = form.cleaned_data['current_balance']
        if 'action' in self.request.POST and self.request.POST['action'] == 'disable account':
            bank_account.status = False
        bank_account.save()
        return super().form_valid(form)
    
class CashCollectCreateView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = CashCollectForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Cash Collection Form'
        return context

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial['post_date'] = datetime.date.today() - datetime.timedelta(days=1) # yesterday
        return initial

    def form_valid(self, form: Any) -> HttpResponse:
        form.instance.collector = self.request.user
        # Add cash to cash depot
        cash_depot = CashDepot.objects.latest('date')
        cash_depot.balance += form.instance.amount
        if form.instance.post_date > cash_depot.date:
            cash_depot.date = form.instance.post_date
        cash_depot.save()

        return super().form_valid(form)

class CashDepositCreateView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = CashDepositForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Cash Deposit Form'
        return context


    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial['post_date'] = datetime.date.today() - datetime.timedelta(days=1) # yesterday
        return initial

    def form_valid(self, form: Any) -> HttpResponse:
        form.instance.depositor = self.request.user
        # Add cash to cash depot
        cash_depot = CashDepot.objects.latest('date')
        cash_depot.balance -= form.instance.amount
        if form.instance.post_date > cash_depot.date:
            cash_depot.date = form.instance.post_date
        cash_depot.save()
        return super().form_valid(form)

class DisburseView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = DisburseForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Disburse Cash Form'
        return context


    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        cash_depot = CashDepot.objects.latest('date')
        cash_depot.balance -= form.instance.amount
        if form.instance.request_date > cash_depot.date:
            cash_depot.date = form.instance.post_date
        cash_depot.save()
        return super().form_valid(form)

class WithdrawalRequestView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = RequestToWithdrawForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Withdrawal Request Form'
        return context

    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        
        return super().form_valid(form)
    
class InterbankTransferView(LoginRequiredMixin, CreateView):
    template_name = 'cashflow/create_form.html'
    form_class = InterbankTransferForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Interbank Transfer Form'
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.performed_by = self.request.user
        form.instance.sender_bank.current_balance -= form.instance.amount
        form.instance.receiver_bank.current_balance += form.instance.amount
        form.instance.sender_bank.save()
        form.instance.receiver_bank.save()
        return super().form_valid(form)
    
class CurrentBalanceUpdateView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = CurrentBalanceUpdateForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Current Balance Update Form'
        return context
    
    def form_valid(self, form: Any) -> HttpResponse:
        bank_account = BankAccount.objects.get(pk=self.kwargs['pk'])
        bank_account.current_balance = form.cleaned_data['current_balance']
        bank_account.save()
        return super().form_valid(form)

class DisableAccountView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/bank_account_form.html'
    form_class = DisableAccountForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['bank_account'] = BankAccount.objects.get(pk=self.kwargs['pk'])
        return context

    def form_valid(self, form: Any) -> HttpResponse:
        bank_account = BankAccount.objects.get(pk=self.kwargs['pk'])
        bank_account.status = False if bank_account.status else True
        bank_account.save()
        return super().form_valid(form)

class ApproveWithdrawalView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/withdraw_form.html'
    form_class = ApproveWithdrawalForm
    success_url = reverse_lazy('cashflow-home')


    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['withdraw_object'] = Withdrawal.objects.get(pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form: Any) -> HttpResponse:
        withdraw_object = Withdrawal.objects.get(pk=self.kwargs['pk'])
        if self.request.POST['decision'] == 'Approved':
            withdraw_object.stage = 1
        if self.request.POST['decision'] == 'Disapproved':
            withdraw_object.stage = -1
        withdraw_object.save()
        return super().form_valid(form)
    
class AdministerWithdrawalView(LoginRequiredMixin, UpdateView):
    model = Withdrawal
    template_name = 'cashflow/create_form.html'
    form_class = AdministerWithdrawalForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Complete Withdrawal Form'
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.stage = 2
        form.instance.bank.current_balance -= form.cleaned_data['amount']
        form.instance.bank.save()
        return super().form_valid(form)
