from django.db import models
from django.utils import timezone
from django.urls import reverse
from stock.models import Product


class DeliveryNote(models.Model):
    delivery_number = models.CharField(max_length=15, unique=True)
    order_number = models.CharField(max_length=15)
    created_date = models.DateField(default=timezone.datetime.today)
    stage = models.CharField(max_length=10, default='CREATED')
    transporter = models.CharField(max_length=50, null=True, blank=True)
    vehicle_number = models.CharField(max_length=10, null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    confirm = models.BooleanField(default=False)
    products = models.JSONField(default=dict)
    source = models.CharField(max_length=50, choices=[('GN', 'Guinness'),
                                                      ('NB', 'Nigerian Breweries'),
                                                      ('IB', "Int'l Breweries"),
                                                      ('SELLWELL', 'Sellwell'),
                                                      ('MD', 'Monument Distillers'),
                                                      ('FAREAST', 'FarEast'),
                                                      ('Hayat', 'Hayat'),
                                                      ])
    ship_to = models.CharField(max_length=20, choices=[('TRADE FAIR', 'Trade fair'),
                                                       ('ISLAND', 'Island'),
                                                       ('BADAGRY', 'Badagry'),
                                                       ('STARDOM', 'Stardom')])
    delivered_to = models.CharField(max_length=20)
    credit = models.BooleanField(default=False)
    remark = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.delivery_number

    def get_absolute_url(self):
        return reverse('delivery-detail', kwargs={'pk': self.pk})