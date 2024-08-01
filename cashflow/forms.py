import datetime

from django import forms
from django.contrib.auth.models import User

from djmoney.forms import MoneyField
from djmoney.money import Money

from .models import (BankAccount, CashCollect, CashDeposit, Disburse, Withdrawal, 
                     InterbankTransfer, CashDepot, BankTransfer, BankCharges)

class ChoiceOrInputWidget(forms.MultiWidget):
    def __init__(self, choices=(), attrs=None):
        # Ensure choices are passed correctly to the Select widget
        widgets = [
            forms.TextInput(attrs={'placeholder': 'Type correct value here if not listed'}),
            forms.Select(choices=choices),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        # Split the value into the expected format for the two widgets
        if value:
            return [None, value]  # Custom input case
        return [None, '']  # Default case

class ChoiceOrInputField(forms.MultiValueField):
    def __init__(self, choices=(), *args, **kwargs):
        self.choices = choices
        widget = ChoiceOrInputWidget(choices=choices)

    # def __init__(self, choices=(), *args, **kwargs):
        fields = [
            forms.ChoiceField(choices=choices, required=False),
            forms.CharField(required=False),
        ]
        super().__init__(fields=fields, require_all_fields=False, widget=widget, *args, **kwargs)
        # self.widget = ChoiceOrInputWidget(choices=choices)

    def compress(self, data_list):
        # If custom input (data_list[1]) is provided, return it; otherwise, return the selected choice
        if data_list[0] == '':
            return data_list[1]
        return data_list[0] if data_list else None

    def clean(self, value):
        # Custom clean method to handle validation
        # if not value or (value[0] in [None, ''] and value[1] in [None, '']):
        #     raise forms.ValidationError("This field is required.")
        # Ensure that a valid choice or custom input is provided
        # if value[0] not in dict(self.choices) and not value[1]:
        #     raise forms.ValidationError("Enter a valid choice or provide a custom value.")
        return self.compress(value)

class BankAccountForm(forms.ModelForm):
    category = forms.ChoiceField(choices=[('Business', 'Business'), ('Admin', 'Admin')])

    class Meta:
        model = BankAccount
        fields = ('account_number', 'name', 'short_name', 'opening_balance', 'category')

class CashCollectForm(forms.ModelForm):
    OPTIONS = (
        ('K1', 'Kwara One'),
        ('K2', 'Kwara Two'),
        ('MSS', 'MSS'),
        ('FG', 'FG')
    )

    source = ChoiceOrInputField(choices=OPTIONS, label='Select or Enter')
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_source(self):
        data = self.cleaned_data['source']
        return data
    
    class Meta:
        model = CashCollect
        fields = ('source', 'amount', 'post_date')

class CashDepositForm(forms.ModelForm):
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = CashDeposit
        fields = ('bank', 'amount', 'post_date')
    
    def clean(self):
        if CashDepot.objects.exists():
            cash = CashDepot.objects.latest('date').balance
            if self.cleaned_data['amount'] > cash:
                raise forms.ValidationError('Insufficient Cash to Deposit !!!')

class DisburseForm(forms.ModelForm):
    request_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = Disburse
        fields = ('requested_by', 'purpose', 'amount', 'request_date')
    
    def clean(self):
        if CashDepot.objects.exists():
            cash = CashDepot.objects.latest('date').balance
            if self.cleaned_data['amount'] > cash:
                raise forms.ValidationError('Your Cash is insufficient !!!')

class CurrentBalanceUpdateForm(forms.Form):
    current_balance = MoneyField(max_digits=12, decimal_places=2, min_value=0)
    date = forms.DateField(widget=forms.DateInput({'type': 'date'}), initial=datetime.date.today)

class DisableAccountForm(forms.Form):
    pass    

class RequestToWithdrawForm(forms.ModelForm):
    party = ChoiceOrInputField(choices=[
        ('GN', 'Guinness'), 
        ('NB', 'Nigerian Breweries'), 
        ('IB', 'International Breweries')])
    # amount = MoneyField(max_digits=12, decimal_places=2)

    class Meta:
        model = Withdrawal
        fields = ('party', 'amount')

class InterbankTransferForm(forms.ModelForm):
    queryset = BankAccount.objects.filter(status=True)
    sender_bank = forms.ModelChoiceField(queryset, empty_label='------', label='From')
    receiver_bank = forms.ModelChoiceField(queryset, empty_label='------', label='To')
    
    class Meta:
        model = InterbankTransfer
        fields = ('sender_bank', 'receiver_bank', 'amount')

    def clean(self):
        if self.cleaned_data['sender_bank'] == self.cleaned_data['receiver_bank']:
            raise forms.ValidationError('Sender and Receiver must not be the same')
        if self.cleaned_data['sender_bank'].current_balance <= self.cleaned_data['amount']:
            raise forms.ValidationError('Insufficient bank balance')
        
class ApproveWithdrawalForm(forms.Form):
    remark = forms.CharField(label='Make a note', required=False, 
                             widget=forms.TextInput(attrs={'placeholder': 'Drop a comment if any'}))

class AdministerWithdrawalForm(forms.ModelForm):

    party = forms.CharField(disabled=True)
    amount = MoneyField(disabled=True)
    particulars = forms.CharField(widget=forms.TextInput(attrs={'placeholder': '--e.g cheque number'}))
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), empty_label='--chose bank with enough balance', required=True)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    requested_by = forms.ModelChoiceField(queryset=User.objects.all(), disabled=True) # active or not does not matter since field is disabled
    

    class Meta:
        model = Withdrawal
        fields = ('party', 'amount', 'requested_by', 'bank', 'particulars', 'post_date')

    def clean(self):
        if self.cleaned_data.get('bank').current_balance <= self.cleaned_data['amount']:
            raise forms.ValidationError('Insufficient bank balance')

class BankTransactionForm(forms.ModelForm):
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), empty_label='-------')
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=datetime.date.today)
    
    class Meta:
        model = BankTransfer
        exclude = ['processed_by']