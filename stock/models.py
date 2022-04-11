from django.db import models
from djmoney.models.fields import MoneyField
from django.shortcuts import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from djmoney.money import Money
from outlet.models import SalesCenter
from core.models import JsonDataset



class ChoiceOption:
    json_dict = JsonDataset.objects.get(pk=1).dataset
    SOURCES = [(i, i) for i in json_dict['product-source']]
    CATEGORY = [(i, i) for i in json_dict['product-category']]
    UNITS = [(i, i) for i in json_dict['product-units']]
    PACKS = [(i, i) for i in json_dict['product-packs']]
    STATES = [(i, i) for i in json_dict['product-states']]
    VOLUME_UNITS = [(i, i) for i in json_dict['product-volume-units']]
    PARAMETERS = [(i, i) for i in json_dict['product-parameters']]

class Product(models.Model):
    name = models.CharField(max_length=20)
    source = models.CharField(max_length=50,
                              choices=ChoiceOption.SOURCES)
    category = models.CharField(max_length=50, choices=ChoiceOption.CATEGORY)
    unit_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    pack_type = models.CharField(max_length=20, default='Pack',
                                 choices=ChoiceOption.PACKS)
    quantity_per_pack = models.IntegerField(default=24)
    unit_type = models.CharField(max_length=20,
                                 default='Can',
                                 choices=ChoiceOption.UNITS,)
    product_state = models.CharField(max_length=20, default='Liquid', choices=ChoiceOption.STATES)
    size_value = models.FloatField(default=33, blank=True, null=True)
    size_value_unit = models.CharField(max_length=20, default='cl',
                                       choices=ChoiceOption.VOLUME_UNITS, blank=True,
                                       null=True)
    alcohol_content = models.FloatField(default=0.0)
    vat = models.FloatField(default=7.5, choices=[(7.5, 'Vatable'), (0.0, 'Exempted')])
    image = models.ImageField(default='default.jpg', upload_to='product_pics')
    cost_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN', 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Cost price can't be NGN0.00")])
    parameter = models.CharField(max_length=20, choices=ChoiceOption.PARAMETERS, default='Normal',
                                 help_text='<span class="text-danger">types but of same price e.g. maltina classic, maltina pineaple</span>')
    active = models.BooleanField(default=True, choices=[(True, 'Yes'), (False, 'No')], verbose_name='Active?')
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20,
                                     choices=[
                                         ('PP', 'Per Pack'),
                                         ('PERCENT', 'Percent'),
                                         ('VALUE', 'Absolute Value'),
                                         ('RATIO', 'Qty Ratio')
                                     ], default='PP')
    date_modified = models.DateTimeField(default=timezone.now)
    is_stock_valued = models.BooleanField(default=False) #

    
    def __str__(self):
        return f"{self.name} {self.parameter} {self.unit_type}~{self.size_value}{self.size_value_unit}x{self.quantity_per_pack}{self.pack_type}"

    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'pk': self.pk})

    def margin(self):
        return self.unit_price - self.cost_price

    
    
class ProductPerformance(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    outlet = models.ForeignKey(SalesCenter, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    landing_cost = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    selling_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    depletion = models.IntegerField()
    balance = models.IntegerField()
    tag = models.BooleanField(default=True) #focus brand

    def __str__(self):
        return f'{self.product} performance' 

    def get_absolute_url(self):
        return reverse('product-performance-detail', kwargs={'pk':self.pk})
        
    
class ProductExtension(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cost_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN',
        default=Money(1000, 'NGN'), 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Cost price can't be NGN0.00")]
    )
    selling_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN',
        default=Money(1000, 'NGN'), 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Selling price can't be NGN0.00")]
    )
    stock_value = models.IntegerField(default=0)
    date = models.DateField(default=timezone.now)
    sell_out = models.IntegerField(default=0)
    sales_amount = MoneyField(
        max_digits=12, decimal_places=2, default_currency='NGN',
        default=Money(0, 'NGN'), 
        validators=[MinValueValidator(Money(0, 'NGN'), 
        message="Sales amount can't be negative")]
    )
    status = models.BooleanField(default=False) # can be used to deactivate the product

    def __str__(self) -> str:
        return f'{self.product}-{self.date}'

    def get_absolute_url(self):
        return reverse('product-ext-detail', kwargs={'pk':self.pk})
    
    def value_of_stock(self):
        return self.cost_price * self.stock_value

    