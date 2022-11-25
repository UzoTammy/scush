from django import forms
from .models import ProductExtension, Product
from core.models import JsonDataset


class ChoiceOption:
    json_dict = JsonDataset.objects.get(pk=1).dataset
    SOURCES = [(i, i) for i in json_dict['product-source']]
    CATEGORY = [(i, i) for i in json_dict['product-category']]
    UNITS = [(i, i) for i in json_dict['product-units']]
    PACKS = [(i, i) for i in json_dict['product-packs']]
    STATES = [(i, i) for i in json_dict['product-states']]
    VOLUME_UNITS = [(i, i) for i in json_dict['product-volume-units']]
    

class FormProduct(forms.ModelForm):
    source = forms.ChoiceField(choices=ChoiceOption.SOURCES, initial='NB')
    category = forms.ChoiceField(choices=ChoiceOption.CATEGORY, initial='Malt')
    units = forms.ChoiceField(choices=ChoiceOption.UNITS, initial='Pack')
    packs = forms.ChoiceField(choices=ChoiceOption.PACKS)
    product_state = forms.ChoiceField(choices=ChoiceOption.STATES, initial='Liquid')
    size_value_unit = forms.ChoiceField(choices=ChoiceOption.VOLUME_UNITS, initial='CL')
    
    class Meta:
        model = Product
        exclude = ['date_modified', 'units']


class ProductExtensionUpdateForm(forms.ModelForm):

    class Meta:
        model = ProductExtension
        fields = ('cost_price', 'selling_price', 'stock_value', 'sell_out', 'sales_amount')
        