from django import forms
from .models import ProductExtension, Product
from core.models import Setting


def get_choice_options():
    def choices(key, fallback):
        return [(i, i) for i in Setting.get_list(key, [fallback])]

    return {
        'SOURCES':      choices('product_source',       'NB'),
        'CATEGORY':     choices('product_category',     'Malt'),
        'UNITS':        choices('product_units',        'Pack'),
        'PACKS':        choices('product_packs',        '1'),
        'STATES':       choices('product_states',       'Liquid'),
        'VOLUME_UNITS': choices('product_volume_units', 'CL'),
    }


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
