from django import forms
from django.forms import ModelForm
from django import forms
from .models import TradeMonthly

class TradeMonthlyForm(ModelForm):
    year = forms.IntegerField(required=False)
    period = forms.CharField(max_length=20, required=False)
    class Meta:
        model = TradeMonthly
        fields = '__all__'