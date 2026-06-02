from django.contrib import admin
from .models import (TradeDaily, TradeMonthly, BalanceSheet,
                     BankAccount, BankBalance, TradeAuditLog, TradeAdjustmentRequest)

admin.site.register(TradeDaily)
admin.site.register(TradeMonthly)
admin.site.register(BalanceSheet)
admin.site.register(BankAccount)
admin.site.register(BankBalance)


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
