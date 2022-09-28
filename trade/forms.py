from django import forms
from django.db.models import fields
from django.forms.widgets import DateInput
from .models import BalanceSheet, TradeMonthly, TradeDaily
import datetime
from djmoney.models.validators import MinMoneyValidator
# from djmoney.models.fields import MoneyField
from djmoney.money import Money
from djmoney.forms.fields import MoneyField


class TradeMonthlyForm(forms.ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = TradeMonthly
        fields = '__all__'

class TradeDailyForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    # start_date = forms.DateTimeField(widget=DateTimeInput(attrs={
    #     'class':'form-control col-6', 'type':'datetime-local'
    # }))
    
    # sales = MoneyField(validators=[MinMoneyValidator(1), MinMoneyValidator(Money(1, 'NGN'))], 
    # help_text='1.00 instead of 0.00')
    # purchase = MoneyField(validators=[MinMoneyValidator(1), MinMoneyValidator(Money(1, 'NGN'))], 
    # help_text='1.00 instead of 0.00')
    
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
class BSForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    class Meta:
        model = BalanceSheet
        fields = '__all__'