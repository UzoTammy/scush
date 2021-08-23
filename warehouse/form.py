from .models import Stores
from django import forms
from django.forms import ModelForm
import datetime


class StoreForm(ModelForm):
    expiry_date = forms.DateField(
        widget=forms.DateInput(format='%d-%m-%Y',
                               attrs={'type': 'date',
                                      'value': datetime.date.today()}
                               ))

    class Meta:
        model = Stores
        fields = '__all__'
