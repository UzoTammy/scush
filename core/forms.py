import json
from django import forms
from django.conf import settings


file_dir = settings.BASE_DIR /'core'/ 'static'/ 'json'/ 'choices.json'

class AddChoicesForm(forms.Form):
    with open(file_dir) as rf:
        content = json.load(rf)
    
    choices = []
    for key, value in content.items():
        sorted_value = sorted(value)
        content[key] = sorted_value

    for key, value in content.items():
        string = ''
        for item in value:
            colon = '.' if item == value[-1] else ','
            string += ' ' + item + colon
            
        choices.append((key, f'{key.upper()}:{string}'))    

    select = forms.ChoiceField(widget=forms.RadioSelect, choices=choices, label='Pick What To Add')
    input_value = forms.CharField(max_length=30, label='New Value')

    class Meta:
        fields = ('select', 'input_value')

class EditChoicesForm(forms.Form):
    with open(file_dir) as rf:
        content = json.load(rf)
    choices = list()
    for key, value in content.items():
        for I, item in enumerate(value):
            choices.append((f"{key}-{item}", f"{item} from {key.upper()} data"))
    select = forms.ChoiceField(widget=forms.RadioSelect, choices=choices, label='Pick What To Edit')
    input_value = forms.CharField(max_length=30, label='New Value')

    
class DeleteChoicesForm(forms.Form):
    with open(file_dir) as rf:
        content = json.load(rf)
    choices = list()
    for key, value in content.items():
        for I, item in enumerate(value):
            choices.append((f"{key}-{item}", f"{item} from {key.upper()} data"))
    select = forms.ChoiceField(widget=forms.RadioSelect, choices=choices, label='Pick What To Delete')
    