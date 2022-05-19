from django import forms
from .models import ProductExtension


class DateInput(forms.DateInput):
    input_type = 'date'
    
class ProductExtensionForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput)

    class Meta:
        model = ProductExtension
        fields = ('product', 'date', 'stock_value', 'sell_out')
        