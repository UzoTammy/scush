from django import forms
from django.forms.widgets import DateInput
from .models import (BalanceSheet, 
                    TradeMonthly, 
                    TradeDaily, 
                    BankAccount, 
                    BankBalance
                    )



class TradeMonthlyForm(forms.ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = TradeMonthly
        fields = '__all__'

class TradeDailyForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))
    
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
class BSForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))


    class Meta:
        model = BalanceSheet
        fields = '__all__'

class BankAccountForm(forms.ModelForm):
    account_group = forms.ChoiceField(initial='Business', choices=[('Business', 'Business'), ('Admin', 'Admin')])
    bank = forms.ChoiceField(choices=[
        ('UBA', 'UBA'), ('Sterling', 'Sterling'), ('Access', 'Access'), ('Heritage', 'Heritage'),
    ])

    class Meta:
        model = BankAccount
        fields = ('account_name', 'nickname', 'account_number', 'bank', 'account_group')

class BankBalanceForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    class Meta:
        model = BankBalance
        fields = '__all__'