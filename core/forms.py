from django import forms
from django.contrib.auth.forms import AuthenticationForm

class JsonDatasetForm(forms.Form):
    input_value = forms.CharField(max_length=30, label='New Value')


class MyDateInput(forms.DateInput):
    pass
    

class MyAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(required=False)    