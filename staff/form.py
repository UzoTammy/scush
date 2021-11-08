from django.forms import ModelForm
from django import forms
from .models import CreditNote, DebitNote, Employee
import json

class CreditForm(ModelForm):
    class Meta:
        model = CreditNote
        exclude = ('status',)


class DebitForm(ModelForm):

    class Meta:
        model = DebitNote
        exclude = ('status',)


class EmployeeForm(ModelForm):
    with open('extrafiles/choices.json') as jsf:
        content = json.load(jsf)

    BANKS = sorted(list((i, i) for i in content['banks']))
    BRANCHES = sorted(list((i, i) for i in content['branches']))
    POSITIONS = sorted(list((i, i) for i in content['positions']))
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


