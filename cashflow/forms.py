import datetime

from django import forms
from django.contrib.auth.models import User

from djmoney.forms import MoneyField
from djmoney.money import Money

from .models import (BankAccount, CashCenter, CashCollect, CashDeposit, Disburse, Withdrawal, 
                     InterbankTransfer, CashDepot, BankTransfer, BankCharges)

class ChoiceOrInputWidget(forms.MultiWidget):
    def __init__(self, choices=(), attrs=None):
        # Ensure choices are passed correctly to the Select widget
        widgets = [
            forms.TextInput(attrs={'placeholder': 'Enter item not listed below'}),
            forms.Select(choices=choices),
            # forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='Cash Center (From)')
    

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
    opening_balance_date = forms.DateField(widget=forms.DateInput({'type': 'date'}), initial=datetime.date.today)


    class Meta:
        model = BankAccount
        fields = ('account_number', 'name', 'short_name', 'opening_balance', 'opening_balance_date', 'category')

class CashCollectForm(forms.Form):
    CASHCENTERS = [
        ("Kwara One", "Kwara One"),
        ("Kwara Two", "kwara Two"),
        ("Kwara Three", "Kwara Three"),
        ("Front Gate", "Front Gate")
    ]

    source = ChoiceOrInputField(choices=CASHCENTERS, label='Cash Center or Customer')
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean_source(self):
        data = self.cleaned_data['source']
        return data
    
    # class Meta:
    #     model = CashCollect
    #     fields = ('cash_center', 'amount', 'post_date')

class CashDepositForm(forms.Form):
    cash_center = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='Cash Center (From)')
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.all(), label='Bank (To)')
    post_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    amount = MoneyField(max_digits=12, decimal_places=2)
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['cash_center'].current_balance:
            raise forms.ValidationError('Insufficient Cash to Deposit !!!')

class InterCashTransferForm(forms.Form):
    donor = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='From')
    receiver = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='To')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['donor'].current_balance:
            raise forms.ValidationError('Not enough cash to transfer !!!')

class DisburseCashForm(forms.Form):
    receiver = forms.CharField(max_length=50)
    donor = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='Cash Center')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['donor'].current_balance:
            raise forms.ValidationError('Not enough cash to disburse !!!')


class CurrentBalanceUpdateForm(forms.Form):
    current_balance = MoneyField(max_digits=12, decimal_places=2, min_value=0)
    date = forms.DateField(widget=forms.DateInput({'type': 'date'}), initial=datetime.date.today)

class DisableAccountForm(forms.Form):
    pass    

class RequestToWithdrawForm(forms.Form):
    party = ChoiceOrInputField(choices=[
        ('GN', 'Guinness'), 
        ('NB', 'Nigerian Breweries'), 
        ('IB', 'International Breweries')])
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True))
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=datetime.date.today)
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['bank'].current_balance:
            raise forms.ValidationError('Not enough balance to fund')
    

class InterbankTransferForm(forms.Form):

    donor = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), label='From')
    receiver = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), label='To')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['donor'].current_balance:
            raise forms.ValidationError(f'Not enough funds in donor {self.cleaned_data["donor.name"]} !!!')
        if self.cleaned_data['donor'] == self.cleaned_data['receiver']:
            raise forms.ValidationError("Donor and receiver account must not be the same")
        
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

class BankTransferForm(forms.Form):
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True))
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=datetime.date.today)
    amount = MoneyField(max_digits=12, decimal_places=2)
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['bank'].current_balance:
            raise forms.ValidationError('Insufficient balance')

class CashCenterCreateForm(forms.ModelForm):
    opening_balance_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = CashCenter
        fields = ['name', 'opening_balance_date', 'opening_balance']