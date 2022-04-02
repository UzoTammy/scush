import json
import datetime
from django.conf import settings
from django.forms import ModelForm
from django import forms
from django.forms.widgets import DateTimeInput
from .models import CreditNote, DebitNote, Employee, RequestPermission



class CreditForm(ModelForm):
    class Meta:
        model = CreditNote
        exclude = ('status',)


class DebitForm(ModelForm):

    class Meta:
        model = DebitNote
        exclude = ('status',)


class EmployeeForm(ModelForm):
    root_dir = settings.BASE_DIR #Path(__file__).resolve().parent.parent

    with open(root_dir /'core'/'static'/ 'json' / 'choices.json') as jsf:
        content = json.load(jsf)

    if content['banks']:
        BANKS = sorted(list((i, i) for i in content['banks']))
    if content['branches']:
        BRANCHES = sorted(list((i, i) for i in content['branches']))
    if content['positions']:
        POSITIONS = sorted(list((i, i) for i in content['positions']))
    if content['departments']:
        DEPARTMENTS = sorted(list((i, i) for i in content['departments']))

    BRANCHES.append(('', '----------'))
    POSITIONS.append(('', '----------'))
    DEPARTMENTS.append(('', '----------'))


    banker = forms.ChoiceField(choices=BANKS, initial='UBA')
    branch = forms.ChoiceField(choices=BRANCHES, required=False)
    position = forms.ChoiceField(choices=POSITIONS, required=False)
    department = forms.ChoiceField(choices=DEPARTMENTS, required=False)

    class Meta:
        model = Employee
        fields = ('date_employed', 'is_management', 'position',
              'department', 'branch', 'banker', 'account_number',
              'basic_salary', 'allowance', 'tax_amount')


class DateTimeSelectorWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        days = [(day, str(day).zfill(2)) for day in range(1, 32)]
        months = [(month, str(month).zfill(2)) for month in range(1, 13)]
        year = datetime.date.today().year
        years = [(year, str(year)) for year in [year, year+1]]
        hours = [(hour, str(hour).zfill(2)) for hour in range(24)]
        minutes = [(minute, str(minute).zfill(2)) for minute in range(60)]
        widgets = [
            forms.Select(attrs=attrs, choices=days),
            forms.Select(attrs=attrs, choices=months),
            forms.Select(attrs=attrs, choices=years),
            forms.Select(attrs=attrs, choices=hours),
            forms.Select(attrs=attrs, choices=minutes),
            
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, datetime.datetime):
            return [value.day, value.month, value.year, value.hour, value.minute]
        elif isinstance(value, str):
            date = value.split(' ')[0]
            time = value.split(' ')[1]
            year, month, day = date.split('-') #value.split('-')
            hour, minute = time.split(':')
            return [day, month, year, hour, minute]
        return [None, None, None, None, None]

    def value_from_datadict(self, data, files, name):
        day, month, year, hour, minute = super().value_from_datadict(data, files, name)
        # DateField expects a single string that it can parse into a date.
        return f'{year}-{month}-{day} {hour}:{minute}'


class RequestPermissionForm(ModelForm):
    start_date = forms.DateTimeField(widget=DateTimeInput(attrs={
        'class':'form-control col-6', 'type':'datetime-local'
    }))
    resume_date = forms.DateTimeField(widget=DateTimeInput(attrs={
        'class':'form-control col-6', 'type': 'datetime-local'
    }))
    
    class Meta:
        model = RequestPermission
        fields = ('staff', 'reason', 'start_date', 'resume_date')
    
        