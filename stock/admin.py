from django.contrib import admin
from .models import (Product, ProductExtension, ProductPerformance, PriceHistory, Category, Source, StockMovement,
                     StockCountSession, StockCountLine, StockLocation)

# Register your models here.
admin.site.register(Product)
admin.site.register(ProductExtension)
admin.site.register(ProductPerformance)
admin.site.register(PriceHistory)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'date', 'location', 'reference', 'created_by']
    list_filter = ['movement_type', 'date', 'location']
    search_fields = ['product__name', 'reference', 'note']


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'branch', 'address', 'active']
    list_editable = ['code', 'address', 'active']
    list_filter = ['branch', 'active']
    search_fields = ['name', 'code']


class StockCountLineInline(admin.TabularInline):
    model = StockCountLine
    extra = 0


@admin.register(StockCountSession)
class StockCountSessionAdmin(admin.ModelAdmin):
    list_display = ['date', 'note', 'created_by', 'created_at']
    list_filter = ['date']
    inlines = [StockCountLineInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    list_editable = ['active']
    search_fields = ['name']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['code', 'label', 'contact_person', 'phone', 'email', 'lead_time_days', 'active']
    list_editable = ['label', 'contact_person', 'phone', 'email', 'lead_time_days', 'active']
    search_fields = ['code', 'label', 'contact_person']
