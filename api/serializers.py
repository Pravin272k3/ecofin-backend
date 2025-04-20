from rest_framework import serializers
from accounts.models import User, UserProfile
from banking.models import Account, Transaction, Transfer, Statement
from transactions.models import Category, EnhancedTransaction, Tag, RecurringGroup
from budgets.models import Budget, BudgetItem
from goals.models import Goal, GoalContribution

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'preferred_currency', 'theme_preference', 'language_preference']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'profile']
        read_only_fields = ['id']
        extra_kwargs = {'email': {'required': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', None),
            date_of_birth=validated_data.get('date_of_birth', None)
        )
        return user

class AccountSerializer(serializers.ModelSerializer):
    account_type_name = serializers.ReadOnlyField(source='account_type.name')

    class Meta:
        model = Account
        fields = ['id', 'account_number', 'account_type', 'account_type_name', 'balance', 'currency', 'status', 'created_at', 'nickname']
        read_only_fields = ['id', 'account_number', 'balance', 'created_at']

class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.ReadOnlyField(source='account.account_number')

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'account_number', 'transaction_type', 'amount', 'balance_after', 'description', 'created_at', 'reference_number']
        read_only_fields = ['id', 'account', 'transaction_type', 'amount', 'balance_after', 'created_at', 'reference_number']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'category_type', 'icon', 'color', 'parent', 'is_system']
        read_only_fields = ['id', 'is_system']

class EnhancedTransactionSerializer(serializers.ModelSerializer):
    bank_transaction = TransactionSerializer(read_only=True)
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = EnhancedTransaction
        fields = ['id', 'bank_transaction', 'category', 'category_name', 'notes', 'location', 'is_recurring', 'is_split']
        read_only_fields = ['id', 'bank_transaction']

class BudgetItemSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    spent = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = BudgetItem
        fields = ['id', 'budget', 'category', 'category_name', 'amount', 'spent', 'remaining', 'progress_percentage']
        read_only_fields = ['id', 'budget']

class BudgetSerializer(serializers.ModelSerializer):
    items = BudgetItemSerializer(many=True, read_only=True)
    spent = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = ['id', 'name', 'amount', 'period', 'start_date', 'end_date', 'is_active', 'created_at', 'updated_at', 'items', 'spent', 'remaining', 'progress_percentage']
        read_only_fields = ['id', 'created_at', 'updated_at']

class GoalContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalContribution
        fields = ['id', 'goal', 'amount', 'date', 'notes', 'from_account']
        read_only_fields = ['id', 'goal']

class GoalSerializer(serializers.ModelSerializer):
    contributions = GoalContributionSerializer(many=True, read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_on_track = serializers.ReadOnlyField()

    class Meta:
        model = Goal
        fields = ['id', 'name', 'goal_type', 'target_amount', 'current_amount', 'start_date', 'target_date', 'status', 'description', 'icon', 'color', 'created_at', 'updated_at', 'contributions', 'progress_percentage', 'days_remaining', 'is_on_track']
        read_only_fields = ['id', 'current_amount', 'created_at', 'updated_at']
