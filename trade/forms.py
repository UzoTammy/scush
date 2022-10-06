from django import forms
from django.forms.widgets import DateInput
from .models import BalanceSheet, TradeMonthly, TradeDaily



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