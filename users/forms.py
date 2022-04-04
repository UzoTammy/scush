import datetime
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import Profile
from apply.models import Applicant


class MyForm(forms.ModelForm):

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
                  )

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                 'placeholder': 'enter first name',
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
                                                 years=list(range(1973,
                                                                  datetime.date.today().year - 15))
                                                 ),
            'course': forms.TextInput(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'course of study'}),
            'email': forms.TextInput(attrs={'class': 'form-control mb-2',
                                            'placeholder': 'e.g. name@gmail.com'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control mb-2',
                                             'placeholder': '08012345678'}),
            'address': forms.Textarea(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'Residential address and not more than 100 characters',
                                             'rows': 5},
                                      )

        }


class UserRegisterForm(UserCreationForm):
    # email = forms.EmailField()
    # first_name = forms.CharField(max_length=30)
    # last_name = forms.CharField(max_length=30)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['password1', 'password2']
        # fields = UserCreationForm.Meta.fields

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['staff']

