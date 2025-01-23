import datetime
from itertools import chain
from typing import Any
from django.db.models.base import Model as Model
from django.db.models import Sum
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

from .forms import (BankAccountForm, CashCenterCreateForm, CashCollectForm, CashDepositForm,
                    CurrentBalanceUpdateForm, RequestToWithdrawForm, InterbankTransferForm,
                    DisableAccountForm, ApproveWithdrawalForm, AdministerWithdrawalForm,
                    BankTransferForm, InterCashTransferForm, DisburseCashForm)

from .models import BankAccount, BankTransaction, CashCenter, CashDepot, Withdrawal, CashDeposit, BankTransfer, InterbankTransfer, BankCharges
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
    paginate_by = 7
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
        cash_center_queryset = CashCenter.objects.filter(status=True)
        context['cash_center'] = cash_center_queryset
        context['cash'] = Money(cash_center_queryset.exclude(name='Imprest Cash Center').aggregate(Sum('current_balance'))['current_balance__sum'], 'NGN')
        context['imprest_cash'] = cash_center_queryset.get(name='Imprest Cash Center').current_balance
        
        context['current_bank_balance_total_business'] = QuerySum.to_currency(BankAccount.objects.filter(status=True).filter(category='Business'), 'current_balance')
        context['current_bank_balance_total_admin'] = QuerySum.to_currency(BankAccount.objects.filter(status=True).filter(category='Admin'), 'current_balance')
        
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
    
class CashCollectCreateView(LoginRequiredMixin, FormView):
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
        source = form.cleaned_data['source']
        description = form.cleaned_data['description'] or f'Cash received from {source}'
        receiver = CashCenter.objects.get(name='Main Cash Center')
        receiver.deposit(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        messages.success(self.request, 'Cash Accepted Successfully !!!')
        return super().form_valid(form)

class CashDepositCreateView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = CashDepositForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Cash Deposit'
        return context

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial['post_date'] = datetime.date.today() - datetime.timedelta(days=1) # yesterday
        initial['cash_center'] = CashCenter.objects.get(pk=1)
        # initial['bank'] = BankAccount.objects.get(pk='')
        return initial

    def form_valid(self, form: Any) -> HttpResponse:
        bank = form.cleaned_data['bank']
        timestamp = form.cleaned_data['post_date']
        amount = form.cleaned_data['amount']
        description = form.cleaned_data['description'] or "cash deposit"
        cash_center = form.cleaned_data['cash_center']

        bank.deposit(amount, description, timestamp, self.request.user)
        cash_center.withdraw(amount, description, timestamp, self.request.user)
        
        messages.success(self.request, 'Cash Deposited Successfully !!!')
        return super().form_valid(form)
        
class InterCashTransferView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = InterCashTransferForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Disburse Cash Form'
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        donor: CashCenter = form.cleaned_data['donor']
        receiver: CashCenter = form.cleaned_data['receiver']
        description = form.cleaned_data['description'] or f'From {donor} to {receiver}'
        donor.withdraw(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        receiver.deposit(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        messages.success(self.request, 'Cash exchanged Successfully !!!')
        return super().form_valid(form)

class WithdrawalRequestView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = RequestToWithdrawForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Withdrawal Request Form'
        return context

    def form_valid(self, form):
        form.cleaned_data['requested_by'] = self.request.user
         # send mail
        # email = EmailMessage(
        # subject=f'Withdrawal Request {form.cleaned_data["amount"]}',
        # body = loader.render_to_string('cashflow/mail_withdraw_request.html', 
        #                                context={'withdraw_object': form.cleaned_data, 'url_link':f"{self.request.META['HTTP_ORIGIN']}/cashflow/" }
        #                             ),
        # from_email='noreply@scush.com.ng',
        # to=['uzo.nwokoro@ozonefl.com'],
        # cc=[self.request.user.email, 'abasiama.ibanga@ozonefl.com'],
        # headers={'message-id': 'tiger'}
        # )
        # email.content_subtype='html'
        # email.send(fail_silently=True)

        bank: BankAccount  = form.cleaned_data['bank']
        bank.withdraw(form.cleaned_data['amount'], form.cleaned_data['description'], form.cleaned_data['post_date'], self.request.user)

        messages.success(self.request, 'Your request is submitted !!!')
        return super().form_valid(form)
    
class InterbankTransferView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = InterbankTransferForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Interbank Transfer Form'
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        donor: BankAccount = form.cleaned_data['donor']
        receiver: BankAccount = form.cleaned_data['receiver']
        description = form.cleaned_data['description'] or 'Interbank transfer'
        donor.withdraw(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        receiver.deposit(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        
        messages.success(self.request, 'Transfer made successfully !!!')
        return super().form_valid(form)
    
    
class DisburseCashView(LoginRequiredMixin, FormView):
    template_name = 'cashflow/create_form.html'
    form_class = DisburseCashForm
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Disburse Cash Form'
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        donor: BankAccount = form.cleaned_data['donor']
        description = form.cleaned_data['description'] or f'Cash disbursed to {form.cleaned_data["receiver"]}'
        donor.withdraw(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        
        messages.success(self.request, 'Cash disbursed successfully !!!')
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

class BankTransferView(LoginRequiredMixin, FormView):
    form_class = BankTransferForm
    template_name = 'cashflow/create_form.html'
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Bank Transfer Form'
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        description = form.cleaned_data['description'] or 'Direct Transfer'
        bank: BankAccount = form.cleaned_data['bank']

        bank.deposit(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        
        messages.success(self.request, 'Direct Deposited Successfully !!!')
        return super().form_valid(form)
    
class BankChargesView(LoginRequiredMixin, FormView):
    form_class = BankTransferForm
    template_name = 'cashflow/create_form.html'
    success_url = reverse_lazy('cashflow-home')

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['heading'] = 'Bank Charges Form'
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        description = form.cleaned_data['description'] or 'Bank Reconciliation Charges'
        bank: BankAccount = form.cleaned_data['bank']
        bank.withdraw(form.cleaned_data['amount'], description, form.cleaned_data['post_date'], self.request.user)
        messages.success(self.request, 'Bank Charge debited successfully !!!')
        return super().form_valid(form)

class BankStatementView(LoginRequiredMixin, DetailView):
    model = BankAccount
    template_name = 'cashflow/statement.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.get_object().transactions.all().order_by('timestamp')
        
        self.get_object().reset_current_balance()
        return context
    
class CashCenterCreateView(LoginRequiredMixin, CreateView):
    form_class = CashCenterCreateForm
    success_url = reverse_lazy('cashflow-home')
    template_name = 'cashflow/create_form.html'
    
    def form_valid(self, form):
        form.instance.current_balance = form.instance.opening_balance
        form.save()
        messages.success(self.request, f'{form.cleaned_data["name"]} created successfully !!!')
        return super().form_valid(form) 

class CashStatementView(LoginRequiredMixin, DetailView):
    model = CashCenter
    template_name = 'cashflow/statement.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.get_object().cash_transactions.all().order_by('timestamp')
        
        self.get_object().reset_current_balance()
        return context
    