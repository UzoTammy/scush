import datetime
from typing import Any

from .models import Stores, StoreLevy, BankAccount
from core.models import JsonDataset

from django.shortcuts import get_object_or_404
from django import forms




class StoreForm(forms.ModelForm):
    expiry_date = forms.DateField(
        widget=forms.DateInput(
                               attrs={'type': 'date',
                                      'value': datetime.date.today}
                               ))

    class Meta:
        model = Stores
        fields = '__all__'

class StoreLevyForm(forms.ModelForm):
    payment_date = forms.DateField(
        widget=forms.DateInput(
                               attrs={'type': 'date',
                                      'value': datetime.date.today}
                               ))
    class Meta:
        model = StoreLevy
        fields = '__all__'

    
    

class BankAccountForm(forms.ModelForm):
    json_data = get_object_or_404(JsonDataset, pk=1).dataset

    try:
        banks = list((bank, bank) for bank in json_data['banks']) if json_data['banks'] else [(None, '------')]
    except KeyError:
        banks = [('UBA', 'UBA')]

    name = forms.CharField(label='Account Name')
    bank = forms.ChoiceField(choices=banks)
    
    class Meta:
        model = BankAccount
        fields = ['name', 'account_number', 'bank']