from django import forms
from .models import CustomerProfile
from django.core.validators import RegexValidator

TYPE_CHOICES = [('NA', 'Non-Alcoholic'), ('A', 'Alcoholic'), ('U', 'Unknown')]
SECTION_CHOICES = [('C & B', 'Crate & Bottle'), ('W & W', 'Wine & Whisky'), ('C & P', 'Cans & Pet')]

class CustomerProfileForm(forms.ModelForm):
    # type = forms.MultipleChoiceField(choices=TYPE_CHOICES)
    section = forms.MultipleChoiceField(choices=SECTION_CHOICES)
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
                  'section',
                  'sales',
                  'freq']