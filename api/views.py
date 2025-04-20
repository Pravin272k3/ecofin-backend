from rest_framework import viewsets, permissions, status, serializers
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes

from accounts.models import User, UserProfile
from banking.models import Account, Transaction, Transfer, Statement
from transactions.models import Category, EnhancedTransaction, Tag, RecurringGroup
from budgets.models import Budget, BudgetItem
from goals.models import Goal, GoalContribution

from .serializers import (
    UserSerializer, UserProfileSerializer, AccountSerializer,
    TransactionSerializer, CategorySerializer, EnhancedTransactionSerializer,
    BudgetSerializer, BudgetItemSerializer, GoalSerializer, GoalContributionSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Allow unauthenticated access for registration (create)
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        # Regular users can only see their own profile
        if not self.request.user.is_staff:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.all()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard data for the current user"""
        user = request.user

        # Get account summary
        accounts = Account.objects.filter(user=user)
        account_summary = {
            'total_balance': accounts.aggregate(Sum('balance'))['balance__sum'] or 0,
            'account_count': accounts.count(),
        }

        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            account__user=user
        ).order_by('-created_at')[:10]

        # Get budget summary
        active_budgets = Budget.objects.filter(user=user, is_active=True)
        budget_summary = {
            'budget_count': active_budgets.count(),
            'total_budget': active_budgets.aggregate(Sum('amount'))['amount__sum'] or 0,
        }

        # Get goal summary
        active_goals = Goal.objects.filter(user=user).exclude(status='completed')
        goal_summary = {
            'goal_count': active_goals.count(),
            'total_goal_amount': active_goals.aggregate(Sum('target_amount'))['target_amount__sum'] or 0,
            'total_current_amount': active_goals.aggregate(Sum('current_amount'))['current_amount__sum'] or 0,
        }

        # Combine all data
        dashboard_data = {
            'account_summary': account_summary,
            'recent_transactions': TransactionSerializer(recent_transactions, many=True).data,
            'budget_summary': budget_summary,
            'goal_summary': goal_summary,
        }

        return Response(dashboard_data)

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own accounts
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get accounts from the banking system that are not yet linked to the EcoFin app"""
        # Get the user's email to match with banking system accounts
        user_email = request.user.email
        print(f"Looking for accounts for user email: {user_email}")

        # Get accounts already linked to the EcoFin app
        linked_account_numbers = set(Account.objects.filter(user=request.user).values_list('account_number', flat=True))
        print(f"Already linked account numbers: {linked_account_numbers}")

        # Get accounts from the banking system that match the user's email and are not yet linked
        from banking.models import Account as BankingAccount
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get the user from the banking system
        banking_users = User.objects.filter(email=user_email)
        print(f"Found {len(banking_users)} users with email {user_email}")

        # Get all banking accounts
        all_banking_accounts = BankingAccount.objects.all()
        print(f"Total banking accounts: {len(all_banking_accounts)}")

        # Get accounts from the banking system that match the user's email
        available_accounts = BankingAccount.objects.filter(user__email=user_email)
        print(f"Found {len(available_accounts)} accounts for user email {user_email}")

        # Filter out accounts that are already linked
        available_accounts = [account for account in available_accounts
                             if account.account_number not in linked_account_numbers]
        print(f"After filtering, {len(available_accounts)} accounts are available to link")

        # Serialize the accounts
        data = []
        for account in available_accounts:
            try:
                account_data = {
                    'id': account.id,
                    'account_number': account.account_number,
                    'account_type': account.account_type.id if account.account_type else None,
                    'account_type_name': account.account_type.name if account.account_type else 'Unknown',
                    'balance': float(account.balance),
                    'currency': account.currency,
                    'status': account.status,
                    'nickname': account.nickname or f'Account {account.account_number}',
                }
                data.append(account_data)
            except Exception as e:
                print(f"Error serializing account {account.id}: {str(e)}")

        return Response(data)

    @action(detail=False, methods=['post'])
    def link(self, request):
        """Link existing accounts from the banking system to the EcoFin app"""
        account_ids = request.data.get('account_ids', [])

        if not account_ids:
            return Response({'error': 'No account IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the banking system accounts
        from banking.models import Account as BankingAccount
        banking_accounts = BankingAccount.objects.filter(id__in=account_ids, user__email=request.user.email)

        if not banking_accounts:
            return Response({'error': 'No valid accounts found'}, status=status.HTTP_404_NOT_FOUND)

        # Link the accounts to the EcoFin app
        linked_accounts = []
        for banking_account in banking_accounts:
            # Check if account is already linked
            if Account.objects.filter(account_number=banking_account.account_number, user=request.user).exists():
                continue

            try:
                # Create a new account in the EcoFin app linked to the banking system account
                account = Account.objects.create(
                    user=request.user,
                    account_number=banking_account.account_number,
                    account_type=banking_account.account_type,
                    balance=banking_account.balance,
                    currency=banking_account.currency,
                    status=banking_account.status,
                    nickname=banking_account.nickname or f'Account {banking_account.account_number}'
                )
            except Exception as e:
                print(f"Error linking account {banking_account.id}: {str(e)}")
                continue
            linked_accounts.append(self.get_serializer(account).data)

        return Response({
            'success': True,
            'message': f'Successfully linked {len(linked_accounts)} accounts',
            'accounts': linked_accounts
        })

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        account = self.get_object()
        amount = request.data.get('amount')

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            from decimal import Decimal
            account.deposit(Decimal(str(amount)))
            return Response({'success': True, 'balance': account.balance})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        account = self.get_object()
        amount = request.data.get('amount')

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            from decimal import Decimal
            account.withdraw(Decimal(str(amount)))
            return Response({'success': True, 'balance': account.balance})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @csrf_exempt
    @action(detail=False, methods=['post'], url_path='link-by-number')
    def link_by_number(self, request):
        """Link an account by account number"""
        account_number = request.data.get('account_number')
        nickname = request.data.get('nickname')

        if not account_number:
            return Response({'error': 'Account number is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the account exists in the banking system
        from banking.models import Account as BankingAccount
        try:
            banking_account = BankingAccount.objects.get(account_number=account_number)

            # Check if the account belongs to the user (by email)
            if banking_account.user.email != request.user.email:
                return Response({'error': 'This account does not belong to you'}, status=status.HTTP_403_FORBIDDEN)

            # Check if the account is already linked
            if Account.objects.filter(account_number=account_number, user=request.user).exists():
                return Response({'error': 'This account is already linked'}, status=status.HTTP_400_BAD_REQUEST)

            # Link the account
            account = Account.objects.create(
                user=request.user,
                account_number=banking_account.account_number,
                account_type=banking_account.account_type,
                balance=banking_account.balance,
                currency=banking_account.currency,
                status=banking_account.status,
                nickname=nickname or banking_account.nickname or f'Account {banking_account.account_number}'
            )

            return Response({
                'success': True,
                'message': 'Account linked successfully',
                'account': self.get_serializer(account).data
            })

        except BankingAccount.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        source_account = self.get_object()
        destination_id = request.data.get('destination_account')
        amount = request.data.get('amount')

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            # Verify destination account belongs to user
            try:
                destination_account = Account.objects.get(id=destination_id, user=request.user)
            except Account.DoesNotExist:
                return Response({'error': 'Destination account not found'}, status=status.HTTP_404_NOT_FOUND)

            from decimal import Decimal
            transfer = source_account.transfer(destination_account, Decimal(str(amount)))
            return Response({
                'success': True,
                'source_balance': source_account.balance,
                'destination_balance': destination_account.balance,
                'reference': str(transfer.reference_number)
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see transactions from their accounts
        queryset = Transaction.objects.filter(account__user=self.request.user)

        # Filter by account if specified
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)

        # Filter by transaction type if specified
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # Filter by date range if specified
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Debug the filter parameters
        print(f"Filtering transactions with:")
        print(f"Account ID: {account_id}")
        print(f"Transaction Type: {transaction_type}")
        print(f"Start Date: {start_date}")
        print(f"End Date: {end_date}")
        print(f"Query: {queryset.query}")

        return queryset

    @action(detail=False, methods=['get'])
    def recent(self, request):
        transactions = self.get_queryset().order_by('-created_at')[:20]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        # Get transactions grouped by category
        enhanced_transactions = EnhancedTransaction.objects.filter(
            bank_transaction__account__user=request.user
        )

        # Group by category
        category_data = {}
        for et in enhanced_transactions:
            category_name = et.category.name if et.category else 'Uncategorized'
            if category_name not in category_data:
                category_data[category_name] = {
                    'count': 0,
                    'total': 0,
                }

            category_data[category_name]['count'] += 1
            category_data[category_name]['total'] += et.bank_transaction.amount

        return Response(category_data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can see system categories and their own categories
        return Category.objects.filter(is_system=True) | Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_system=False)

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own budgets
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        budget = self.get_object()
        items = BudgetItem.objects.filter(budget=budget)
        serializer = BudgetItemSerializer(items, many=True)
        return Response(serializer.data)

class BudgetItemViewSet(viewsets.ModelViewSet):
    queryset = BudgetItem.objects.all()
    serializer_class = BudgetItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see budget items from their budgets
        return BudgetItem.objects.filter(budget__user=self.request.user)

    def perform_create(self, serializer):
        # Ensure the budget belongs to the user
        budget_id = self.request.data.get('budget')
        try:
            budget = Budget.objects.get(id=budget_id, user=self.request.user)
            serializer.save(budget=budget)
        except Budget.DoesNotExist:
            raise serializers.ValidationError({'budget': 'Budget not found or does not belong to you'})


class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own goals
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def contribute(self, request, pk=None):
        goal = self.get_object()
        amount = request.data.get('amount')
        notes = request.data.get('notes', '')
        account_id = request.data.get('account_id')

        try:
            # Handle amount conversion safely
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            # Get account if provided
            account = None
            if account_id:
                try:
                    account = Account.objects.get(id=account_id, user=request.user)
                except Account.DoesNotExist:
                    return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

            # Create contribution with proper decimal conversion
            from decimal import Decimal
            contribution = GoalContribution.objects.create(
                goal=goal,
                amount=Decimal(str(amount)),  # Convert to Decimal safely
                notes=notes,
                from_account=account
            )

            # If account provided, withdraw the amount
            if account:
                try:
                    account.withdraw(Decimal(str(amount)))  # Convert to Decimal safely
                except ValueError as e:
                    # Rollback contribution if withdrawal fails
                    contribution.delete()
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'current_amount': goal.current_amount,
                'progress': goal.progress_percentage
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
