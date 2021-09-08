from django import forms
from .models import CustomerProfile
from django.core.validators import RegexValidator

CHOICES = [('A-Can', 'Alcoholic, Cans'),
           ('NA-Can', 'Non-alcoholic, Cans'),
           ('Wine', 'Wine'),
           ('A-Bottle', 'Alcoholic, Bottles'),
           ('NA-Bottle', 'Non-alcoholic, Bottles'),
           ]


class CustomerProfileForm(forms.ModelForm):
    type = forms.MultipleChoiceField(choices=CHOICES)
    number_regex = RegexValidator(regex=r'0\d{10}', message='only numbers starting with zero')
    mobile = forms.CharField(max_length=11, validators=[number_regex])

    class Meta:
        model = CustomerProfile
        fields = ['business_name',
                  'business_owner',
                  'cluster',
                  'mobile',
                  'email',
                  'address',
                  'type',
                  'sales',
                  'freq']