from django import forms
from django.db.models import fields
from .models import TradeMonthly, TradeDaily
import datetime

class TradeMonthlyForm(forms.ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = TradeMonthly
        fields = '__all__'

class TradeDailyForm(forms.ModelForm):
    date = forms.DateField(initial=datetime.date.today(), help_text='yyyy-mm-dd')
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
    