from django import forms
from .models import ProductExtension, Product
from core.models import JsonDataset


class ChoiceOption:
    try:
        json_obj =  JsonDataset.objects.get(pk=1)
        if json_obj:
            json_dict = json_obj.dataset
            SOURCES = [(i, i) for i in json_dict['product-source']]
            CATEGORY = [(i, i) for i in json_dict['product-category']]
            UNITS = [(i, i) for i in json_dict['product-units']]
            PACKS = [(i, i) for i in json_dict['product-packs']]
            STATES = [(i, i) for i in json_dict['product-states']]
            VOLUME_UNITS = [(i, i) for i in json_dict['product-volume-units']]
    except Exception as err:
        str(err)    
    

class FormProduct(forms.ModelForm):
    
    source = forms.ChoiceField(choices=ChoiceOption.SOURCES, initial='NB')
    category = forms.ChoiceField(choices=ChoiceOption.CATEGORY, initial='Malt')
    units = forms.ChoiceField(choices=ChoiceOption.UNITS, initial='Pack')
    packs = forms.ChoiceField(choices=ChoiceOption.PACKS)
    product_state = forms.ChoiceField(choices=ChoiceOption.STATES, initial='Liquid')
    size_value_unit = forms.ChoiceField(choices=ChoiceOption.VOLUME_UNITS, initial='CL')
    velocity = forms.ChoiceField(choices=[
                                            [-1, "Not Determined"], 
                                            [0, "No Sellout"], 
                                            [1, "Very Low Sellout"], 
                                            [2, "Low Sellout"], 
                                            [3, "Moderate Sellout"],
                                            [4, "High Sellout"],
                                            [5, "Very High Sellout"]
                                        ]
                                )
    
    class Meta:
        model = Product
        exclude = ['date_modified', 'units']


class ProductExtensionUpdateForm(forms.ModelForm):

    class Meta:
        model = ProductExtension
        fields = ('cost_price', 'selling_price', 'stock_value', 'sell_out', 'sales_amount')
        