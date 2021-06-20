from django import forms
import datetime
from apply.models import Applicant


class ApplicantForm(forms.ModelForm):

    class Meta:
        model = Applicant
        fields = ('first_name',
                  'second_name',
                  'last_name',
                  'gender',
                  'marital_status',
                  'qualification',
                  'birth_date',
                  'course',
                  'email',
                  'mobile',
                  'address',
                  # 'status',
                  )

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                 'placeholder': 'enter first name',
                                                 'error_messages': {'required': 'Enter name'},
                                                 },
                                          ),
            'second_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                  'placeholder': 'enter middle name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                'placeholder': 'enter surname'}),
            'gender': forms.RadioSelect(),
            'marital_status': forms.RadioSelect(),
            'qualification': forms.Select(attrs={'class': 'form-control'},
                                          choices=[
                                              ('NON', 'Non'), ('PRIMARY', 'Primary'),
                                              ('SECONDARY', 'Secondary'),
                                              ('ND/NCE', 'ND or NCE'),
                                              ('HND/HCE', 'HND or HCE'),
                                              ('BACHELOR', 'First Degree'),
                                              ('MASTERS', 'Masters'),
                                          ]),
            'birth_date': forms.SelectDateWidget(attrs={'class': 'form-control '},
                                                 years=list(range(1960,
                                                                  datetime.date.today().year - 16))
                                                 ),
            'course': forms.TextInput(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'e.g. Accounting'}),
            'email': forms.TextInput(attrs={'class': 'form-control mb-2',
                                            'placeholder': 'e.g. name@gmail.com',
                                            'required': False}),
            'mobile': forms.TextInput(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'e.g. 080-1234-5678', 'cols': 60}),
            'address': forms.Textarea(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'Residential address and not more than 100 characters',
                                             'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'})
        }


class MyForm(forms.Form):
    name = forms.CharField(max_length=20, help_text='surname first')
    age = forms.IntegerField()
    email_address = forms.EmailField()

