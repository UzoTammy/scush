from django.db import models
from djmoney.models.fields import MoneyField
from django.shortcuts import reverse

SOURCES = [('NB', 'NBPlc'),
           ('GN', 'GNPlc'),
           ('IB', "Int'l Plc"),
           ('FE', 'FarEast'),
           ('SW', 'SellWell'),
           ('MD', 'Monument'),
           ('FN', 'Fouani'),
           ('MSC', 'Miscellaneous'),
           ('Hayat', 'Hayat')]

CATEGORIES = [('Malt', 'Malt'),
              ('Lager', 'Lager'),
              ('Stout', 'Stout'),
              ('RTD', 'RTD'),
              ('ED', 'Energy Drink'),
              ('Bitters', 'Bitters'),
              ('Soft', 'Soft Drink'),
              ('H2O', 'Water'),
              ('NA Wine', 'Non Alcoholic Wine'),
              ('Wine', 'Alcoholic Wine')]

UNITS = [('Pieces', 'Pieces'),
         ("Pack", 'Pack'),
         ('Pallet', 'Pallet')]

PACKS = [('Can', 'Can'), ('Pet', 'Pet'), ('Bottle', 'Bottle'), ('Tetra', 'Tetra Pak'), ('Crate', 'Crate')]

STATES = [('Liquid', 'Liquid'), ('Solid', 'Solid'), ('Gas', 'Gas')]

SIZE_VALUE_UNIT = [('ml', 'Millilitres'),
                   ('cl', 'Centilitres'),
                   ('l', 'Litres')]
PARAMETER = [('Classic', 'Classic'), ('Ultra', 'Ultra'), ('Mini', 'Mini')]


class Product(models.Model):
    name = models.CharField(max_length=20)
    source = models.CharField(max_length=50,
                              choices=SOURCES)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    unit_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN')
    pack_type = models.CharField(max_length=20, default='Pack',
                                 choices=UNITS)
    quantity_per_pack = models.IntegerField(default=24)
    unit_type = models.CharField(max_length=20, default='Can')
    product_state = models.CharField(max_length=20, default='Liquid', choices=STATES)
    size_value = models.FloatField(default=33, blank=True, null=True)
    size_value_unit = models.CharField(max_length=20, default='cl',
                                       choices=SIZE_VALUE_UNIT, blank=True,
                                       null=True)
    alcohol_content = models.FloatField(default=0.0)
    vat = models.FloatField(default=7.5, choices=[(7.5, 'Vatted'), (0.0, 'Exempted')])
    image = models.ImageField(default='default.jpg', upload_to='product_pics')
    cost_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    parameter = models.CharField(max_length=20,
                                 help_text='<span class="text-danger">types but of same price e.g. maltina classic, maltina pineaple</span>')
    active = models.BooleanField(default=True, choices=[(True, 'Active'), (False, 'Inactive')])

    def __str__(self):
        return f"{self.name} {self.unit_type}~{self.size_value}{self.size_value_unit}x{self.quantity_per_pack}{self.pack_type}"

    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'pk': self.pk})
