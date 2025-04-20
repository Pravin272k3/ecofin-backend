from django.db import models
from django.conf import settings
from transactions.models import Category
from django.utils import timezone

class Budget(models.Model):
    """Budget model for tracking spending limits"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)  # Only for custom periods
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.amount} ({self.get_period_display()})"

    @property
    def spent(self):
        """Calculate amount spent in this budget period"""
        return sum(item.spent for item in self.items.all())

    @property
    def remaining(self):
        """Calculate remaining budget"""
        return self.amount - self.spent

    @property
    def progress_percentage(self):
        """Calculate percentage of budget used"""
        if self.amount == 0:
            return 100 if self.spent > 0 else 0
        return min(100, (self.spent / self.amount) * 100)

class BudgetItem(models.Model):
    """Individual category within a budget"""
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budget_items')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} - {self.amount}"

    @property
    def spent(self):
        """Calculate amount spent in this category during the budget period"""
        from transactions.models import EnhancedTransaction

        # Get date range based on budget period
        start_date = self.budget.start_date
        if self.budget.period == 'custom' and self.budget.end_date:
            end_date = self.budget.end_date
        else:
            # Calculate end date based on period
            if self.budget.period == 'daily':
                end_date = start_date
            elif self.budget.period == 'weekly':
                end_date = start_date + timezone.timedelta(days=7)
            elif self.budget.period == 'monthly':
                # Approximate a month
                end_date = start_date + timezone.timedelta(days=30)
            elif self.budget.period == 'quarterly':
                end_date = start_date + timezone.timedelta(days=90)
            elif self.budget.period == 'yearly':
                end_date = start_date + timezone.timedelta(days=365)
            else:
                end_date = timezone.now().date()

        # Query transactions in this category within the date range
        transactions = EnhancedTransaction.objects.filter(
            category=self.category,
            bank_transaction__created_at__date__gte=start_date,
            bank_transaction__created_at__date__lte=end_date,
            bank_transaction__account__user=self.budget.user
        )

        # Sum transaction amounts
        return sum(t.bank_transaction.amount for t in transactions if t.bank_transaction.transaction_type in ['withdrawal', 'transfer_out'])

    @property
    def remaining(self):
        """Calculate remaining budget for this category"""
        return self.amount - self.spent

    @property
    def progress_percentage(self):
        """Calculate percentage of category budget used"""
        if self.amount == 0:
            return 100 if self.spent > 0 else 0
        return min(100, (self.spent / self.amount) * 100)

class BudgetAlert(models.Model):
    """Alerts for budget thresholds"""
    THRESHOLD_CHOICES = [
        (50, '50% Used'),
        (75, '75% Used'),
        (90, '90% Used'),
        (100, '100% Used (Budget Reached)'),
        (110, '110% Used (Budget Exceeded)'),
    ]

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='alerts')
    threshold_percentage = models.IntegerField(choices=THRESHOLD_CHOICES)
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['budget', 'threshold_percentage']

    def __str__(self):
        return f"{self.budget.name} - {self.threshold_percentage}% Alert"
