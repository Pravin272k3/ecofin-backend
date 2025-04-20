from django.contrib import admin
from .models import Budget, BudgetItem, BudgetAlert

class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 1

class BudgetAlertInline(admin.TabularInline):
    model = BudgetAlert
    extra = 1

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'amount', 'period', 'start_date', 'end_date', 'is_active')
    list_filter = ('period', 'is_active', 'created_at')
    search_fields = ('name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [BudgetItemInline, BudgetAlertInline]

@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('budget', 'category', 'amount')
    list_filter = ('budget__period', 'category')
    search_fields = ('budget__name', 'category__name')

@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ('budget', 'threshold_percentage', 'is_active', 'last_triggered')
    list_filter = ('threshold_percentage', 'is_active')
    search_fields = ('budget__name',)
