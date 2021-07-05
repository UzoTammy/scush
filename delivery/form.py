from django import forms
from stock.models import Product
from .models import DeliveryNote
import datetime


class DeliveryFormCreate(forms.ModelForm):
    delivery_number = forms.CharField(min_length=3,
                                      max_length=12)
    order_number = forms.CharField(min_length=3,
                                   max_length=12)
    created_date = forms.DateField(
        widget=forms.DateInput(format='%d-%m-%Y',
                               attrs={'type': 'date',
                                      'value': datetime.date.today()}
                               )
    )
    source = forms.ChoiceField(choices=[('GN', 'Guinness'),
                                        ('NB', 'Nigerian Breweries'),
                                        ('IB', "Int'l Breweries"),
                                        ('SELLWELL', 'Sellwell'),
                                        ('MD', 'Monument Distillers'),
                                        ('FAREAST', 'FarEast'),
                                        ('Hayat', 'Hayat'),
                                        ])
    ship_to = forms.ChoiceField(choices=[('TRADE FAIR', 'Trade fair'),
                                         ('ISLAND', 'Island'),
                                         ('BADAGRY', 'Badagry'),
                                         ('STARDOM', 'Stardom')])

    class Meta:
        model = DeliveryNote
        fields = ('delivery_number', 'order_number', 'created_date', 'source', 'ship_to')


class DeliveryFormDeliver(forms.ModelForm):
    transporter = forms.CharField()
    vehicle_number = forms.CharField(max_length=10)
    delivery_date = forms.DateField(help_text=f"<small style='color: red;'>Date format:dd/mm/yyyy",
                                    widget=forms.DateInput(attrs={'type': 'date'})
    )
    delivered_to = forms.ChoiceField(choices=[('TRADE FAIR', 'Trade fair'),
                                            ('ISLAND', 'Island'),
                                            ('BADAGRY', 'Badagry'),
                                            ('STARDOM', 'Stardom')])

    class Meta:
        model = DeliveryNote
        fields = ('transporter', 'vehicle_number', 'delivery_date', 'delivered_to')


class DeliveryFormReturn(forms.Form):
    product_1 = forms.ModelChoiceField(queryset=Product.objects.filter(active=True), label='First Product')
    quantity_delivered_1 = forms.IntegerField(min_value=0, label='Quantity Delivered')
    quantity_received_1 = forms.IntegerField(min_value=0, label='Quantity Received')

    product_2 = forms.ModelChoiceField(queryset=Product.objects.all(),
                                       required=False,
                                       label='Second Product')
    quantity_delivered_2 = forms.IntegerField(min_value=0,
                                              required=False,
                                              label='Quantity Delivered')
    quantity_received_2 = forms.IntegerField(min_value=0,
                                             required=False,
                                             label='Quantity Received')

    product_3 = forms.ModelChoiceField(queryset=Product.objects.all(), required=False, label='Third Product')
    quantity_delivered_3 = forms.IntegerField(min_value=0,
                                              required=False,
                                              label='Quantity Delivered')
    quantity_received_3 = forms.IntegerField(min_value=0,
                                             required=False,
                                             label='Quantity Received')



