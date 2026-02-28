from django import forms
from .models import ProductExtension, Product
from core.models import JsonDataset


def get_choice_options():
    """Load choices from database at runtime, not at import time."""
    defaults = {
        'SOURCES': [('NB', 'NB')],
        'CATEGORY': [('Malt', 'Malt')],
        'UNITS': [('Pack', 'Pack')],
        'PACKS': [('1', '1')],
        'STATES': [('Liquid', 'Liquid')],
        'VOLUME_UNITS': [('CL', 'CL')],
    }
    
    try:
        json_obj = JsonDataset.objects.get(pk=1)
        if json_obj and json_obj.dataset:
            json_dict = json_obj.dataset
            return {
                'SOURCES': [(i, i) for i in json_dict.get('product-source', defaults['SOURCES'])],
                'CATEGORY': [(i, i) for i in json_dict.get('product-category', defaults['CATEGORY'])],
                'UNITS': [(i, i) for i in json_dict.get('product-units', defaults['UNITS'])],
                'PACKS': [(i, i) for i in json_dict.get('product-packs', defaults['PACKS'])],
                'STATES': [(i, i) for i in json_dict.get('product-states', defaults['STATES'])],
                'VOLUME_UNITS': [(i, i) for i in json_dict.get('product-volume-units', defaults['VOLUME_UNITS'])],
            }
    except (JsonDataset.DoesNotExist, Exception):
        pass
    
    return defaults


class FormProduct(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_choice_options()
        
        self.fields['source'] = forms.ChoiceField(choices=choices['SOURCES'], initial='NB')
        self.fields['category'] = forms.ChoiceField(choices=choices['CATEGORY'], initial='Malt')
        self.fields['units'] = forms.ChoiceField(choices=choices['UNITS'], initial='Pack')
        self.fields['packs'] = forms.ChoiceField(choices=choices['PACKS'])
        self.fields['product_state'] = forms.ChoiceField(choices=choices['STATES'], initial='Liquid')
        self.fields['size_value_unit'] = forms.ChoiceField(choices=choices['VOLUME_UNITS'], initial='CL')
        self.fields['velocity'] = forms.ChoiceField(choices=[
            [-1, "Not Determined"], 
            [0, "No Sellout"], 
            [1, "Very Low Sellout"], 
            [2, "Low Sellout"], 
            [3, "Moderate Sellout"],
            [4, "High Sellout"],
            [5, "Very High Sellout"]
        ])
    
    class Meta:
        model = Product
        exclude = ['date_modified', 'units']


class ProductExtensionUpdateForm(forms.ModelForm):

    class Meta:
        model = ProductExtension
        fields = ('cost_price', 'selling_price', 'stock_value', 'sell_out', 'sales_amount')
