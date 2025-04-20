from django.contrib import admin
from .models import AccountType, Account, Transfer, Transaction, Statement

@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'interest_rate', 'minimum_balance', 'maintenance_fee')
    search_fields = ('name',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'currency', 'status', 'created_at')
    list_filter = ('status', 'account_type', 'currency', 'created_at')
    search_fields = ('account_number', 'user__email', 'nickname')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'source_account', 'destination_account', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reference_number', 'source_account__account_number', 'destination_account__account_number')
    readonly_fields = ('created_at', 'updated_at', 'reference_number')
    date_hierarchy = 'created_at'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'account', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('reference_number', 'account__account_number', 'description')
    readonly_fields = ('created_at', 'reference_number')
    date_hierarchy = 'created_at'

@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ('account', 'start_date', 'end_date', 'opening_balance', 'closing_balance', 'generated_at')
    list_filter = ('start_date', 'end_date', 'generated_at')
    search_fields = ('account__account_number',)
    readonly_fields = ('generated_at',)
    date_hierarchy = 'generated_at'
