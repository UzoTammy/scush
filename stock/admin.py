from django.contrib import admin
from .models import Product, ProductExtension, ProductPerformance, PriceHistory, Category, Source

# Register your models here.
admin.site.register(Product)
admin.site.register(ProductExtension)
admin.site.register(ProductPerformance)
admin.site.register(PriceHistory)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    list_editable = ['active']
    search_fields = ['name']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['code', 'label', 'active']
    list_editable = ['label', 'active']
    search_fields = ['code', 'label']
