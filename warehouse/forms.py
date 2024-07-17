import datetime
from typing import Any

from .models import Stores, StoreLevy, BankAccount
from core.models import JsonDataset

from django.shortcuts import get_object_or_404
from django import forms
from djmoney.forms.fields import MoneyField

class StoreForm(forms.ModelForm):
    expiry_date = forms.DateField(
        widget=forms.DateInput(
                               attrs={'type': 'date',
                                      'value': datetime.date.today}
                               ))

    class Meta:
        model = Stores
        fields = '__all__'


class PayRentForm(forms.Form):

    months = forms.ChoiceField(choices=[(0, '---')]+[(i, i) for i in range(1, 13)], label='Month(s) paying for', required=False)
    years = forms.ChoiceField(choices=[(0, '---')]+[(i, i) for i in range(1, 6)], label='Year(s) paying for', required=False)
    amount_paid = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    date_paid = forms.DateField(widget=forms.DateInput(
        attrs={'type': 'date', 'value': datetime.date.today() - datetime.timedelta(days=1)}
    ))

    def clean(self):
        if self.cleaned_data['months'] == '0' and self.cleaned_data['years'] == '0':
            raise forms.ValidationError('Both month and year cannot be empty')
        # return super().clean()


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