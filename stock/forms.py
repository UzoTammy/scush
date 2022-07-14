from django import forms
from .models import ProductExtension


    
class ProductExtensionUpdateForm(forms.ModelForm):

    class Meta:
        model = ProductExtension
        fields = ( 'cost_price', 'selling_price', 'stock_value', 'sell_out', 'sales_amount')
        