from django.contrib import admin
from .models import BudgetYear, SalesTarget, KPIBudget, KPIMonthlyTarget


class SalesTargetInline(admin.TabularInline):
    model  = SalesTarget
    extra  = 0
    fields = ('month', 'target')


class KPIBudgetInline(admin.TabularInline):
    model  = KPIBudget
    extra  = 0
    fields = ('metric', 'annual_value')


class KPIMonthlyTargetInline(admin.TabularInline):
    model  = KPIMonthlyTarget
    extra  = 0
    fields = ('month', 'metric', 'target_value')


@admin.register(BudgetYear)
class BudgetYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'sales_budget')
    ordering     = ('-year',)
    inlines      = [SalesTargetInline, KPIBudgetInline, KPIMonthlyTargetInline]


@admin.register(SalesTarget)
class SalesTargetAdmin(admin.ModelAdmin):
    list_display = ('budget_year', 'month', 'target')
    list_filter  = ('budget_year__year',)
    ordering     = ('budget_year__year', 'month')


@admin.register(KPIBudget)
class KPIBudgetAdmin(admin.ModelAdmin):
    list_display = ('budget_year', 'metric', 'annual_value')
    list_filter  = ('budget_year__year', 'metric')
    ordering     = ('-budget_year__year', 'metric')


@admin.register(KPIMonthlyTarget)
class KPIMonthlyTargetAdmin(admin.ModelAdmin):
    list_display = ('budget_year', 'month', 'metric', 'target_value')
    list_filter  = ('budget_year__year', 'metric')
    ordering     = ('-budget_year__year', 'month', 'metric')
