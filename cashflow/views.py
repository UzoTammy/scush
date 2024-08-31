import datetime
from itertools import chain
from typing import Any
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView, CreateView, UpdateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.template import loader
from django.utils.html import format_html

from djmoney.money import Money

from .forms import (BankAccountForm, CashCollectForm, CashDepositForm, DisburseForm, 
                    CurrentBalanceUpdateForm, RequestToWithdrawForm, InterbankTransferForm,
                    DisableAccountForm, ApproveWithdrawalForm, AdministerWithdrawalForm,
                    BankTransactionForm)
from .models import BankAccount, CashDepot, Withdrawal, CashDeposit, BankTransfer, InterbankTransfer, BankCharges
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
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.current_balance = form.instance.opening_balance
        return super().form_valid(form)

class CashflowHomeView(LoginRequiredMixin, FormView, ListView):
    """ 
    1. Display bank accounts, available cash and funds in banks
    2. Provide links to features
        - Collect cash, - bank deposit, - disburse cash, 
        - request to withdraw -> aprrove/disapprove -> administer if approved
        - transfer from bank to bank, - create bank account, - accummulated bank transfers(daily) 
        - accummulated bank charges(daily)
    Cash collect: 
    """
    
    template_name = 'cashflow/home.html'
    form_class = CurrentBalanceUpdateForm
    success_url = reverse_lazy('cashflow-home')
    paginate_by = 4
    model = BankAccount

    
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        if not CashDepot.objects.exists():
            CashDepot.objects.create(
                balance=Money(0, 'NGN'),
                date=datetime.date.today()
            )
        return super().setup(request, *args, **kwargs)
    
    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset()
        if self.request.GET.get('status') == 'all':
            queryset = BankAccount.objects.all()
        else:
            queryset = BankAccount.objects.filter(status=True)
        return queryset.order_by('-category')
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        
        context = super().get_context_data(**kwargs)
        
        # context['object_list'] = queryset
        if CashDepot.objects.all().exists():
            context['cash'] = CashDepot.objects.latest('date').balance
            # context['cash_date'] = CashDepot.objects.latest('date').date
        context['current_bank_balance_total'] = QuerySum.to_currency(BankAccount.objects.filter(status=True), 'current_balance')
        context['pending_withdrawals'] = Withdrawal.objects.exclude(stage=-1).exclude(stage=2) # -1, 0, 1, 2
        
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
        
        messages.success(self.request, 'Cash Accepted Successfully !!!')
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
        
        form.instance.bank.current_balance += form.instance.amount
        form.instance.bank.save()

        messages.success(self.request, 'Cash Deposited Successfully !!!')
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
            cash_depot.date = form.instance.request_date
        cash_depot.save()
        messages.success(self.request, 'Cash Disbursed Successfully !!!')
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
         # send mail
        email = EmailMessage(
        subject=f'Withdrawal Request {form.instance.amount}',
        body = loader.render_to_string('cashflow/mail_withdraw_request.html', 
                                       context={'withdraw_object': form.instance, 'url_link':f"{self.request.META['HTTP_ORIGIN']}/cashflow/" }
                                    ),
        from_email='noreply@scush.com.ng',
        to=['uzo.nwokoro@ozonefl.com'],
        cc=[self.request.user.email, 'abasiama.ibanga@ozonefl.com'],
        headers={'message-id': 'tiger'}
        )
        email.content_subtype='html'
        email.send(fail_silently=True)

        messages.success(self.request, 'Your request have been created !!!')
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
        messages.success(self.request, 'Transfer made successfully !!!')
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
        bank_account.opening_balance_date = form.cleaned_data['date']
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
        
        send_mail(
            subject="Withdrawal Request",
            message='',
            from_email='noreply@scush.com.ng',
            recipient_list=['uzo.nwokoro@ozonefl.com', 'abasiama.ibanga@ozonefl.com', withdraw_object.requested_by.email],
            fail_silently=True,
            html_message=format_html(f'''<p>Request to withdraw {withdraw_object.amount} to {withdraw_object.party} is <bold>APPROVED</bold></p>
                                     <a href="{self.request.META['HTTP_ORIGIN']}/cashflow">Visit Site</a>''')
        )
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

class BankTransferView(LoginRequiredMixin, CreateView):
    form_class = BankTransactionForm
    template_name = 'cashflow/create_form.html'
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Bank Transfer Form'
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.processed_by = self.request.user
        form.instance.bank.current_balance += form.cleaned_data['amount']
        form.instance.bank.save()
        
        return super().form_valid(form)
    
class BankChargesView(LoginRequiredMixin, CreateView):
    form_class = BankTransactionForm
    template_name = 'cashflow/create_form.html'
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Bank Charges Form'
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.processed_by = self.request.user
        form.instance.bank.current_balance -= form.cleaned_data['amount']
        form.instance.bank.save()
        
        return super().form_valid(form)

class BankStatementView(LoginRequiredMixin, DetailView):
    model = BankAccount
    template_name = 'cashflow/bank_statement.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # lets get the date
        # date = self.get_object().opening_balance_date
        # filter deposit
        # deposits = CashDeposit.objects.filter(post_date__gte=date).filter(bank=self.get_object())
        # inter_transfer_in = InterbankTransfer.objects.filter(transfer_date__gte=date).filter(receiver_bank=self.get_object())
        # bank_transfer = BankTransfer.objects.filter(post_date__gte=date).filter(bank=self.get_object())
        # bank_charges = BankCharges.objects.filter(post_date__gte=date).filter(bank=self.get_object())
        # withdrawals = Withdrawal.objects.filter(post_date__gte=date).filter(bank=self.get_object()).filter(stage=2)
        # inter_transfer_out = InterbankTransfer.objects.filter(transfer_date__gte=date).filter(sender_bank=self.get_object())
        # pick out dates
        # d1 = deposits.values_list('post_date', flat=True).distinct() if deposits else CashDeposit.objects.none()
        # d2 = inter_transfer_in.values_list('transfer_date', flat=True).distinct() if inter_transfer_in else CashDeposit.objects.none()
        # d3 = bank_transfer.values_list('post_date', flat=True).distinct() if bank_transfer else CashDeposit.objects.none()
        # d4 = bank_charges.values_list('post_date', flat=True).distinct() if bank_charges else CashDeposit.objects.none()
        # d5 = withdrawals.values_list('post_date', flat=True).distinct() if withdrawals else CashDeposit.objects.none()
        # d6 = inter_transfer_out.values_list('post_date', flat=True).distinct() if inter_transfer_out else CashDeposit.objects.none()
        
        # dates = set(chain(d1,  d2, d3, d4, d5, d6))
        # dict_d1, dict_d2, dict_d3, dict_d4, dict_d5, dict_d6 = dict(), dict(), dict(), dict(), dict(), dict()
        # for date in dates:
        #     if deposits.exists():
        #         deposits.objects.filter(post_date=date)
        return context