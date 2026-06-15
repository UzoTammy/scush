from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field
from .models import ProductExtension, Product, Category, Source, StockMovement, StockLocation
from core.models import Setting


def get_choice_options():
    def choices(key, fallback):
        return [(i, i) for i in Setting.get_list(key, [fallback])]

    return {
        'UNITS':        choices('product_units',        'Pack'),
        'PACKS':        choices('product_packs',        '1'),
        'STATES':       choices('product_states',       'Liquid'),
        'VOLUME_UNITS': choices('product_volume_units', 'CL'),
    }


class FormProduct(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_choice_options()
        
        self.fields['source'] = forms.ModelChoiceField(
            queryset=Source.objects.filter(active=True),
            initial=Source.objects.filter(pk='NB').first(),
        )
        self.fields['category'] = forms.ModelChoiceField(
            queryset=Category.objects.filter(active=True),
            initial=Category.objects.filter(name='Malt').first(),
        )
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

        # Split fields into two columns to keep the form compact
        field_names = list(self.fields.keys())
        midpoint = (len(field_names) + 1) // 2
        left_fields = field_names[:midpoint]
        right_fields = field_names[midpoint:]

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Column(*[Field(f) for f in left_fields], css_class='col-md-6'),
                Column(*[Field(f) for f in right_fields], css_class='col-md-6'),
            )
        )

    class Meta:
        model = Product
        exclude = ['date_modified', 'units']


class ProductExtensionUpdateForm(forms.ModelForm):

    class Meta:
        model = ProductExtension
        fields = ('cost_price', 'selling_price', 'stock_value', 'sell_out', 'sales_amount')


class StockLocationForm(forms.ModelForm):

    class Meta:
        model = StockLocation
        fields = ('name', 'code', 'branch', 'address', 'active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
        }


class StockMovementForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = StockLocation.objects.filter(active=True)
        self.fields['location'].required = False

    class Meta:
        model = StockMovement
        fields = ('movement_type', 'quantity', 'date', 'location', 'reference', 'note')
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
        }
