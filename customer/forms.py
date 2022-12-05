from django import forms
from .models import Profile as CustomerProfile
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
