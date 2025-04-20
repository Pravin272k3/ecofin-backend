from django.db import models
from django.conf import settings
from banking.models import Account, Transaction as BankTransaction

class Category(models.Model):
    """Transaction categories for better organization and analysis"""
    CATEGORY_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('investment', 'Investment'),
    ]

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=50, blank=True, null=True)  # Icon identifier
    color = models.CharField(max_length=7, blank=True, null=True)  # Hex color code
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)  # NULL for system categories
    is_system = models.BooleanField(default=False)  # System categories cannot be modified by users
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class EnhancedTransaction(models.Model):
    """Enhanced transaction model with additional metadata for the EcoFin app"""
    bank_transaction = models.OneToOneField(BankTransaction, on_delete=models.CASCADE, related_name='enhanced_data')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    notes = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField('Tag', blank=True, related_name='transactions')
    location = models.CharField(max_length=255, blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    recurring_group = models.ForeignKey('RecurringGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    is_split = models.BooleanField(default=False)

    def __str__(self):
        return f"Enhanced: {self.bank_transaction}"

class Tag(models.Model):
    """Tags for transactions"""
    name = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags')
    color = models.CharField(max_length=7, blank=True, null=True)  # Hex color code

    class Meta:
        unique_together = ['name', 'user']

    def __str__(self):
        return self.name

class RecurringGroup(models.Model):
    """Group for recurring transactions"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recurring_groups')
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.frequency})"

class SplitTransaction(models.Model):
    """For transactions that are split across multiple categories"""
    parent_transaction = models.ForeignKey(EnhancedTransaction, on_delete=models.CASCADE, related_name='splits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='split_transactions')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Split: {self.amount} from {self.parent_transaction.bank_transaction}"
