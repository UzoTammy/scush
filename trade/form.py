from django import forms
from django.db.models import fields
from django.forms import ModelForm
from django import forms
from .models import TradeMonthly, TradeDaily
import datetime

class TradeMonthlyForm(ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = TradeMonthly
        fields = '__all__'

class TradeDailyForm(ModelForm):
    
    class Meta:
        model = TradeDaily
        fields = '__all__'

    date = forms.DateField(
        widget=forms.DateInput(format='%d-%m-%Y',
                               attrs={'type': 'date',
                                      'value': datetime.date.today
                                      }
                               ))
 