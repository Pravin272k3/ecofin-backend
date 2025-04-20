from django.db import models
from django.conf import settings
from django.utils import timezone

class Goal(models.Model):
    """Financial goals for users"""
    GOAL_TYPES = [
        ('savings', 'Savings'),
        ('debt_payment', 'Debt Payment'),
        ('purchase', 'Major Purchase'),
        ('emergency_fund', 'Emergency Fund'),
        ('retirement', 'Retirement'),
        ('education', 'Education'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField(max_length=15, choices=GOAL_TYPES)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    start_date = models.DateField(default=timezone.now)
    target_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # Icon identifier
    color = models.CharField(max_length=7, blank=True, null=True)  # Hex color code
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.current_amount}/{self.target_amount}"

    @property
    def progress_percentage(self):
        """Calculate percentage of goal achieved"""
        if self.target_amount == 0:
            return 100 if self.current_amount > 0 else 0
        return min(100, (self.current_amount / self.target_amount) * 100)

    @property
    def days_remaining(self):
        """Calculate days remaining until target date"""
        today = timezone.now().date()
        if today > self.target_date:
            return 0
        return (self.target_date - today).days

    @property
    def is_on_track(self):
        """Determine if goal is on track to be completed by target date"""
        if self.status == 'completed':
            return True

        if self.days_remaining == 0:
            return self.progress_percentage >= 100

        # Calculate expected progress based on elapsed time
        total_days = (self.target_date - self.start_date).days
        if total_days <= 0:
            return self.progress_percentage >= 100

        elapsed_days = (timezone.now().date() - self.start_date).days
        expected_progress = (elapsed_days / total_days) * 100

        # Allow for a 10% buffer
        return self.progress_percentage >= (expected_progress - 10)

class GoalContribution(models.Model):
    """Contributions made toward a goal"""
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    from_account = models.ForeignKey('banking.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='goal_contributions')

    def __str__(self):
        return f"{self.goal.name} - {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        # Update the goal's current amount when a contribution is added
        is_new = self.pk is None
        old_amount = 0

        if not is_new:
            # Get the old amount if this is an update
            old_obj = GoalContribution.objects.get(pk=self.pk)
            old_amount = old_obj.amount

        super().save(*args, **kwargs)

        # Update the goal's current amount
        if is_new:
            self.goal.current_amount += self.amount
        else:
            # Adjust for the difference if this is an update
            self.goal.current_amount = self.goal.current_amount - old_amount + self.amount

        # Update goal status if completed
        if self.goal.current_amount >= self.goal.target_amount:
            self.goal.status = 'completed'
        elif self.goal.status == 'not_started':
            self.goal.status = 'in_progress'

        self.goal.save()

class GoalMilestone(models.Model):
    """Milestones for tracking progress toward a goal"""
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.goal.name} - {self.name}"

    @property
    def progress_percentage(self):
        """Calculate percentage of milestone achieved"""
        if self.target_amount == 0:
            return 100 if self.goal.current_amount > 0 else 0
        return min(100, (self.goal.current_amount / self.target_amount) * 100)
