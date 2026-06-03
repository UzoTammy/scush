from django.contrib import admin
from .models import (TradeDaily, TradeMonthly, BalanceSheet,
                     BankAccount, BankBalance, TradeAuditLog, TradeAdjustmentRequest,
                     Creditor, CashProjection)

admin.site.register(TradeDaily)
admin.site.register(TradeMonthly)
admin.site.register(BalanceSheet)
admin.site.register(BankAccount)
admin.site.register(BankBalance)


@admin.register(Creditor)
class CreditorAdmin(admin.ModelAdmin):
    list_display = ('account', 'date', 'amount', 'ledger', 'account_type', 'status')
    list_filter = ('ledger', 'account_type', 'status')
    search_fields = ('account',)
    date_hierarchy = 'date'


@admin.register(CashProjection)
class CashProjectionAdmin(admin.ModelAdmin):
    list_display = ('expected_date', 'description', 'amount', 'flow_type', 'category', 'is_recurring')
    list_filter = ('flow_type', 'category', 'is_recurring')
    date_hierarchy = 'expected_date'


@admin.register(TradeAdjustmentRequest)
class TradeAdjustmentRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_at', 'requester', 'model_name', 'record_str', 'status', 'reviewer')
    list_filter = ('status', 'model_name')
    search_fields = ('record_str', 'requester__username')
    readonly_fields = ('model_name', 'record_id', 'record_str', 'requester',
                       'requested_at', 'proposed_changes', 'reviewed_at')


@admin.register(TradeAuditLog)
class TradeAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'model_name', 'record_str')
    list_filter = ('model_name', 'user')
    search_fields = ('record_str', 'user__username')
    readonly_fields = ('model_name', 'record_id', 'record_str', 'user', 'timestamp', 'changes')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
