from django import forms
from .models import Profile as CustomerProfile, CustomerCredit
import datetime
# from django.core.validators import RegexValidator


class CustomerProfileForm(forms.ModelForm):
    # number_regex = RegexValidator(regex=r'[0-9]{3}-[0-9]{4}-[0-9]{4}')#message=''
    mobile = forms.CharField(max_length=17, 
    help_text='<span class="text-danger">Intl Format: +###-###-###-####</span>')
    second_mobile = forms.CharField(max_length=17, 
    help_text='<span class="text-danger">Intl Format: +###-###-###-####</span>', required=False)

    class Meta:
        model = CustomerProfile
        fields = '__all__'


class CustomerCreditForm(forms.ModelForm):
    one_year_ahead = datetime.date.today() + datetime.timedelta(days=365)
    date_created = forms.DateField(widget=forms.DateInput(attrs={
        'type': 'date'
    }), initial=datetime.date.today)
    
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={
        'type': 'date'
    }), initial=one_year_ahead)
    
    
    class Meta:
        model = CustomerCredit
        fields = ('credit_limit', 'date_created', 'expiry_date')


class ChangeCreditValueForm(forms.ModelForm):

    class Meta:
        model = CustomerCredit
        fields = ['current_credit']