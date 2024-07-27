from django import forms
from staff.models import Employee
from django.contrib.auth.forms import AuthenticationForm

class JsonDatasetForm(forms.Form):
    input_value = forms.CharField(max_length=30, label='New Value')


class MyDateInput(forms.DateInput):
    pass

class TestForm(forms.ModelForm):
    date_employed = forms.DateField(widget=forms.DateInput(attrs={
        'type': 'date'
    }))
    official_email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'firstname.lastname@ozonefl.com'
    }))
    official_mobile = forms.CharField(max_length=13, 
    help_text="<span class='text-danger ml-3'>e.g 080-1234-5678</span>",
     widget=forms.TextInput(attrs={
        'pattern': '[0-9]{3}-[0-9]{4}-[0-9]{4}',
        'placeholder': 'XXX-XXXX-XXXX',
        'length':'20'
        
    }))
    class Meta:
        model = Employee
        fields = "__all__"


class MyAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(required=False)    