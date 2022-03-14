from django.contrib import admin
from .models import Product, ProductExtension

# Register your models here.
admin.site.register(Product)
admin.site.register(ProductExtension)
