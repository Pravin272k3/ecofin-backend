from django.contrib import admin
from .models import Goal, GoalContribution, GoalMilestone

class GoalContributionInline(admin.TabularInline):
    model = GoalContribution
    extra = 1

class GoalMilestoneInline(admin.TabularInline):
    model = GoalMilestone
    extra = 1

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'goal_type', 'target_amount', 'current_amount', 'progress_percentage', 'target_date', 'status')
    list_filter = ('goal_type', 'status', 'created_at')
    search_fields = ('name', 'user__email', 'description')
    readonly_fields = ('created_at', 'updated_at', 'progress_percentage', 'days_remaining', 'is_on_track')
    date_hierarchy = 'created_at'
    inlines = [GoalContributionInline, GoalMilestoneInline]

    def progress_percentage(self, obj):
        return f"{obj.progress_percentage:.2f}%"
    progress_percentage.short_description = 'Progress'

@admin.register(GoalContribution)
class GoalContributionAdmin(admin.ModelAdmin):
    list_display = ('goal', 'amount', 'date', 'from_account')
    list_filter = ('date',)
    search_fields = ('goal__name', 'notes')
    date_hierarchy = 'date'

@admin.register(GoalMilestone)
class GoalMilestoneAdmin(admin.ModelAdmin):
    list_display = ('goal', 'name', 'target_amount', 'target_date', 'is_completed')
    list_filter = ('is_completed', 'target_date')
    search_fields = ('goal__name', 'name')
