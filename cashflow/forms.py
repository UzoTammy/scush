import datetime

from django import forms
from django.contrib.auth.models import User

from djmoney.forms import MoneyField
from djmoney.money import Money

from .models import (BankAccount, CashCenter, CashCollect, CashDeposit, Disburse, Withdrawal, 
                     InterbankTransfer, CashDepot, BankTransfer, BankCharges,
                     BankTransaction, CashTransaction)

class DatalistWidget(forms.TextInput):
    """Text input backed by an HTML5 <datalist> for predefined suggestions."""
    def __init__(self, choices=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        list_id = f'{name}-datalist'
        attrs['list'] = list_id
        attrs.setdefault('autocomplete', 'off')
        input_html = super().render(name, value, attrs, renderer)
        options = ''.join(f'<option value="{v}">' for v, _ in self.choices)
        return f'{input_html}<datalist id="{list_id}">{options}</datalist>'


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

class InterCashTransferForm(forms.Form):
    donor = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='From')
    receiver = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='To')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        donor = self.cleaned_data.get('donor')
        receiver = self.cleaned_data.get('receiver')
        if donor and receiver and donor == receiver:
            raise forms.ValidationError('Source and destination cash centers must be different.')
        if donor and self.cleaned_data.get('amount') and self.cleaned_data['amount'] > donor.current_balance:
            raise forms.ValidationError('Not enough cash to transfer !!!')

class DisburseCashForm(forms.Form):
    receiver = forms.CharField(max_length=50)
    donor = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='Cash Center')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['donor'].current_balance:
            raise forms.ValidationError('Not enough cash to disburse !!!')
        
        if CashTransaction.objects.filter(
                                amount=self.cleaned_data['amount'],
                                timestamp__date=self.cleaned_data['post_date'],
                                description=self.cleaned_data['description']).exists():
            
            raise forms.ValidationError("A similar transaction with this date and amount already exist.")

class CurrentBalanceUpdateForm(forms.Form):
    current_balance = MoneyField(max_digits=12, decimal_places=2, min_value=0)
    date = forms.DateField(widget=forms.DateInput({'type': 'date'}), initial=datetime.date.today)

class DisableAccountForm(forms.Form):
    pass    

class RequestToWithdrawForm(forms.Form):
    PARTIES = [
        ('Guinness', 'Guinness'),
        ('Nigerian Breweries', 'Nigerian Breweries'),
        ('International Breweries', 'International Breweries'),
        ('AVAA', 'AVAA'),
        ('Redbull', 'Redbull'),
    ]
    party = forms.CharField(
        label='Party',
        max_length=100,
        widget=DatalistWidget(choices=PARTIES, attrs={'placeholder': 'Type or pick a party'}),
    )
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True))
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['bank'].current_balance:
            raise forms.ValidationError('Not enough balance to fund')
        
        if BankTransaction.objects.filter(
                                bank=self.cleaned_data['bank'],
                                amount=self.cleaned_data['amount'],
                                timestamp__date=self.cleaned_data['post_date'],
                                description=self.cleaned_data['description']).exists():
            
            raise forms.ValidationError("A transaction on this bank with this date and amount already exist.")
            
class InterbankTransferForm(forms.Form):

    donor = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), label='From')
    receiver = forms.ModelChoiceField(queryset=BankAccount.objects.filter(status=True), label='To')
    amount = MoneyField(max_digits=12, decimal_places=2) 
    post_date = forms.DateField(widget=forms.DateTimeInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        donor = self.cleaned_data.get('donor')
        receiver = self.cleaned_data.get('receiver')
        if donor and receiver and donor == receiver:
            raise forms.ValidationError('Source and destination accounts must be different.')
        if donor and self.cleaned_data.get('amount') and self.cleaned_data['amount'] > donor.current_balance:
            raise forms.ValidationError(f'Not enough funds in {donor.name}.')
        
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
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    amount = MoneyField(max_digits=12, decimal_places=2)
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        
        if BankTransaction.objects.filter(
                                bank=self.cleaned_data['bank'],
                                amount=self.cleaned_data['amount'],
                                timestamp__date=self.cleaned_data['post_date'],
                                description=self.cleaned_data['description']).exists():
            
            raise forms.ValidationError("A transaction on this bank with this date and amount already exist.")
        
class CashCenterCreateForm(forms.ModelForm):

    opening_balance_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = CashCenter
        fields = ['name', 'opening_balance_date', 'opening_balance']

class CashCollectForm(forms.Form):
    CASHCENTERS = [
        ("Kwara One", "Kwara One"),
        ("Kwara Two", "Kwara Two"),
        ("Kwara Three", "Kwara Three"),
        ("Front Gate", "Front Gate"),
    ]

    source = forms.CharField(
        label='Cash Center or Customer',
        max_length=100,
        widget=DatalistWidget(choices=CASHCENTERS, attrs={'placeholder': 'Type or pick a source'}),
    )
    amount = MoneyField(max_digits=12, decimal_places=2)
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        
        if CashTransaction.objects.filter(
                                amount=self.cleaned_data['amount'],
                                timestamp__date=self.cleaned_data['post_date'],
                                description=self.cleaned_data['description']).exists():
            
            raise forms.ValidationError("A similar transaction with this date and amount already exist.")
    
class CashDepositForm(forms.Form):
    cash_center = forms.ModelChoiceField(queryset=CashCenter.objects.filter(status=True), label='Cash Center (From)')
    bank = forms.ModelChoiceField(queryset=BankAccount.objects.all(), label='Bank (To)')
    post_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    amount = MoneyField(max_digits=12, decimal_places=2)
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'comment here if neccessary', 'rows': 2}), required=False)
    
    def clean(self):
        if self.cleaned_data['amount'] > self.cleaned_data['cash_center'].current_balance:
            raise forms.ValidationError('Insufficient Cash to Deposit !!!')

        if BankTransaction.objects.filter(
                                bank=self.cleaned_data['bank'],
                                amount=self.cleaned_data['amount'],
                                timestamp__date=self.cleaned_data['post_date'],
                                description=self.cleaned_data['description']).exists():
            
            raise forms.ValidationError("A transaction on this bank with this date and amount already exist.")
        


# if self.cleaned_data['amount'] > self.cleaned_data['bank'].current_balance:
    # raise forms.ValidationError('Insufficient balance')
        