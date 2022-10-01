from ast import While
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
    
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
class BSForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))


    class Meta:
        model = BalanceSheet
        fields = '__all__'