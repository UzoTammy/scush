from django import forms


class JsonDatasetForm(forms.Form):
    input_value = forms.CharField(max_length=30, label=f'New Value')
