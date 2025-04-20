from django.db import models
from django.conf import settings
import uuid

class AccountType(models.Model):
    """Types of bank accounts (e.g., Checking, Savings)"""
    name = models.CharField(max_length=50)
    description = models.TextField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    minimum_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    maintenance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

class Account(models.Model):
    """Bank account model"""
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('INR', 'Indian Rupee'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('frozen', 'Frozen'),
        ('closed', 'Closed'),
    ]

    account_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts')
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nickname = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.account_number} - {self.user.email}"

    def deposit(self, amount):
        """Add funds to account"""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        self.save()
        Transaction.objects.create(
            account=self,
            transaction_type='deposit',
            amount=amount,
            description=f"Deposit to account {self.account_number}"
        )
        return self.balance

    def withdraw(self, amount):
        """Remove funds from account"""
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.save()
        Transaction.objects.create(
            account=self,
            transaction_type='withdrawal',
            amount=amount,
            description=f"Withdrawal from account {self.account_number}"
        )
        return self.balance

    def transfer(self, destination_account, amount):
        """Transfer funds to another account"""
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")

        # Create a transfer record
        transfer = Transfer.objects.create(
            source_account=self,
            destination_account=destination_account,
            amount=amount,
            status='pending'
        )

        # Perform the transfer
        self.balance -= amount
        self.save()

        destination_account.balance += amount
        destination_account.save()

        # Update transfer status
        transfer.status = 'completed'
        transfer.save()

        # Create transaction records
        Transaction.objects.create(
            account=self,
            transaction_type='transfer_out',
            amount=amount,
            description=f"Transfer to account {destination_account.account_number}",
            related_transfer=transfer
        )

        Transaction.objects.create(
            account=destination_account,
            transaction_type='transfer_in',
            amount=amount,
            description=f"Transfer from account {self.account_number}",
            related_transfer=transfer
        )

        return transfer

class Transfer(models.Model):
    """Record of transfers between accounts"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    source_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transfers_sent')
    destination_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transfers_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reference_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transfer {self.reference_number}: {self.source_account.account_number} → {self.destination_account.account_number}"

class Transaction(models.Model):
    """Record of all account transactions"""
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('interest', 'Interest'),
        ('fee', 'Fee'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    related_transfer = models.ForeignKey(Transfer, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    reference_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Set balance_after if not provided
        if not self.balance_after and self.account:
            self.balance_after = self.account.balance
        super().save(*args, **kwargs)

class Statement(models.Model):
    """Monthly account statements"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statements')
    start_date = models.DateField()
    end_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='statements/', null=True, blank=True)

    def __str__(self):
        return f"Statement for {self.account.account_number} - {self.start_date} to {self.end_date}"
