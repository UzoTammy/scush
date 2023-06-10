import datetime
from django import forms
from django.forms.widgets import DateTimeInput
from django.shortcuts import get_object_or_404
from .models import CreditNote, DebitNote, Employee, RequestPermission, Reassign
from core.models import JsonDataset


class CreditForm(forms.ModelForm):
    credit_date = forms.CharField(widget=forms.DateInput(
        attrs={
            'type': 'date'
        }
    ))
    class Meta:
        model = CreditNote
        exclude = ('status',)


class DebitForm(forms.ModelForm):
    debit_date = forms.CharField(widget=forms.DateInput(
        attrs={
            'type': 'date'
        }
    ))
    class Meta:
        model = DebitNote
        exclude = ('status',)


class EmployeeForm(forms.ModelForm):

    """Get the specific record from database for this form"""
    content = get_object_or_404(JsonDataset, pk=1).dataset
    try:
        BANKS = sorted(list((i, i) for i in content['banks'])) if content['banks'] else [(None, '-----')] 
    except KeyError:
        BANKS = [('UBA', 'UBA')]
    try:
        BRANCHES = sorted(list((i, i) for i in content['branches'])) if content['branches'] else [(None, '-----')]
    except KeyError:
        BRANCHES = [('FG', 'FG')]
    try:    
        POSITIONS = sorted(list((i, i) for i in content['positions'])) if content['positions'] else [(None, '-----')]
    except KeyError:
        POSITIONS = [('GSM', 'GSM')]
    try:        
        DEPARTMENTS = sorted(list((i, i) for i in content['departments'])) if content['departments'] else [(None, '-----')]
    except KeyError:
        DEPARTMENTS = [('Sales', 'Sales')]

    BRANCHES.insert(0, (None, '--------'))
    POSITIONS.insert(0, (None, '--------'))
    DEPARTMENTS.insert(0, (None, '--------'))
    
    
    date_employed = forms.DateField(widget=forms.DateInput(attrs={
        'type': 'date'
    }))
    banker = forms.ChoiceField(choices=BANKS, initial='UBA')
    branch = forms.ChoiceField(choices=BRANCHES, required=False)
    position = forms.ChoiceField(choices=POSITIONS, required=False)
    department = forms.ChoiceField(choices=DEPARTMENTS, required=False)
    salary = forms.CharField(max_length=12, help_text='<small class=text-danger>Note: Currency in Naira</small>')
    
    class Meta:
        model = Employee
        fields = ('date_employed', 'position',
              'department', 'branch', 'banker', 
              'account_number')
        extra = ['salary']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['salary'].widget.attrs['placeholder'] = 'Enter Salary as Approved'

    
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


class RequestPermissionForm(forms.ModelForm):
    start_date = forms.DateTimeField(widget=DateTimeInput(attrs={
        'class':'form-control col-6', 'type':'datetime-local'
    }))
    resume_date = forms.DateTimeField(widget=DateTimeInput(attrs={
        'class':'form-control col-6', 'type': 'datetime-local'
    }))
    
    class Meta:
        model = RequestPermission
        fields = ('staff', 'reason', 'start_date', 'resume_date')
