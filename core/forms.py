from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import CompanyProfile

class JsonDatasetForm(forms.Form):
    input_value = forms.CharField(max_length=30, label='New Value')


class CompanyProfileStaticForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ('legal_name', 'rc_number', 'tin', 'date_incorporated',
                  'registered_address', 'logo')
        widgets = {
            'date_incorporated': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'logo':
                field.widget.attrs.setdefault('class', 'form-control')


class CompanyProfileDynamicForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ('tagline', 'mission', 'vision', 'phone', 'email', 'website',
                  'head_office_address', 'facebook', 'twitter', 'instagram', 'linkedin')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class MyDateInput(forms.DateInput):
    pass
    

class MyAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(required=False)    