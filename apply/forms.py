from django import forms
import datetime
from apply.models import Applicant, Interview, GuarantorDocument


class DateInput(forms.DateInput):
    input_type = 'date'

class ApplicantForm(forms.ModelForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control mb-2',
            'placeholder': 'e.g. name@gmail.com',
        })
    )

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
                                                 'placeholder': 'Enter first name',
                                                 'error_messages': {'required': 'Enter name'},
                                                 },
                                          ),
            'second_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                  'placeholder': 'Enter middle name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control mb-2',
                                                'placeholder': 'Enter last name'}),
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
            # 'birth_date': forms.SelectDateWidget(attrs={'class': 'form-control '},
            #                                      years=list(range(1960,
            #                                                       datetime.date.today().year - 16))
            #                                      ),
            'birth_date': DateInput(attrs={
                'class': 'form-control', 
                'min': f'{datetime.date.today().year-50}-01-01',
                'max': f'{datetime.date.today().year-18}-01-01',
                }),
            'course': forms.TextInput(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'e.g. Accounting or empty if no course',
                                             'type': 'search',
                                             }),
            'mobile': forms.TextInput(attrs={'class': 'form-control mb-2',
                                              'type': 'tel',  
                                              'pattern': "[0-9]{3}-[0-9]{4}-[0-9]{4}",
                                             'placeholder': 'e.g. 080-1234-5678', 'cols': 60}),
            'address': forms.Textarea(attrs={'class': 'form-control mb-2',
                                             'placeholder': 'Residential address and not more than 100 characters',
                                             'rows': 4}),
            # 'status': forms.Select(attrs={'class': 'form-control'})
        }


class InterviewForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = Interview
        fields = ['interviewer', 'result', 'date', 'notes']
        labels = {
            'interviewer': 'Interviewer (Staff Member)',
            'result':      'Interview Result',
            'date':        'Interview Date',
            'notes':       'Notes / Remarks',
        }
        widgets = {
            'result': forms.RadioSelect(),
            'notes':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                            'placeholder': 'Optional remarks'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from staff.models import Employee
        self.fields['interviewer'].queryset = Employee.objects.filter(status=True).order_by(
            'staff__last_name'
        )
        self.fields['interviewer'].widget.attrs.update({'class': 'form-control'})


class GuarantorDocumentForm(forms.ModelForm):
    class Meta:
        model = GuarantorDocument
        fields = ['document']
        labels = {'document': 'Upload Completed & Signed Guarantor Form (with ID attached)'}
        widgets = {'document': forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.pdf,.jpg,.jpeg,.png',
        })}


class InviteRequestForm(forms.Form):
    email = forms.EmailField(
        label='Your Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control mb-2',
            'placeholder': 'e.g. name@gmail.com',
        })
    )


class MyForm(forms.Form):
    name = forms.CharField(max_length=20, help_text='surname first')
    age = forms.IntegerField()
    email_address = forms.EmailField()

