from django.contrib import admin
from .models import Category, EnhancedTransaction, Tag, RecurringGroup, SplitTransaction

class SplitTransactionInline(admin.TabularInline):
    model = SplitTransaction
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'user', 'is_system', 'parent')
    list_filter = ('category_type', 'is_system')
    search_fields = ('name',)

@admin.register(EnhancedTransaction)
class EnhancedTransactionAdmin(admin.ModelAdmin):
    list_display = ('bank_transaction', 'category', 'is_recurring', 'is_split')
    list_filter = ('category', 'is_recurring', 'is_split')
    search_fields = ('bank_transaction__reference_number', 'notes', 'location')
    inlines = [SplitTransactionInline]

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color')
    search_fields = ('name',)

@admin.register(RecurringGroup)
class RecurringGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'frequency', 'start_date', 'end_date', 'is_active', 'expected_amount')
    list_filter = ('frequency', 'is_active')
    search_fields = ('name',)

@admin.register(SplitTransaction)
class SplitTransactionAdmin(admin.ModelAdmin):
    list_display = ('parent_transaction', 'amount', 'category')
    list_filter = ('category',)
