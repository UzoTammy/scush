from django.contrib import admin
from .models import Product, ProductExtension, ProductPerformance, PriceHistory

# Register your models here.
admin.site.register(Product)
admin.site.register(ProductExtension)
admin.site.register(ProductPerformance)
admin.site.register(PriceHistory)
