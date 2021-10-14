from django import forms
from django.db.models import fields
from .models import TradeMonthly, TradeDaily
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
    date = forms.DateField(initial=datetime.date.today(), help_text='yyyy-mm-dd')
    # sales = MoneyField(validators=[MinMoneyValidator(1), MinMoneyValidator(Money(1, 'NGN'))], 
    # help_text='1.00 instead of 0.00')
    # purchase = MoneyField(validators=[MinMoneyValidator(1), MinMoneyValidator(Money(1, 'NGN'))], 
    # help_text='1.00 instead of 0.00')
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
    