from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.http import HttpResponse
import uuid
import random
import string
import csv
import io
from datetime import datetime, timedelta

from .models import Account, AccountType, Transaction, Transfer, Statement
from .forms import AccountForm, DepositForm, WithdrawForm, TransferForm

def home(request):
    """Banking home page"""
    if request.user.is_authenticated:
        accounts = Account.objects.filter(user=request.user)
        total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0

        # Only get transactions if there are accounts
        if accounts.exists():
            recent_transactions = Transaction.objects.filter(
                account__user=request.user
            ).order_by('-created_at')[:5]
        else:
            recent_transactions = []

        context = {
            'accounts': accounts,
            'total_balance': total_balance,
            'recent_transactions': recent_transactions,
        }
        return render(request, 'banking/home.html', context)
    else:
        return render(request, 'banking/landing.html')

@login_required
def account_list(request):
    """List all accounts for the current user"""
    accounts = Account.objects.filter(user=request.user)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0

    context = {
        'accounts': accounts,
        'total_balance': total_balance,
    }
    return render(request, 'banking/account_list.html', context)

@login_required
def account_create(request):
    """Create a new account"""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user

            # Generate a unique account number
            while True:
                account_number = ''.join(random.choices(string.digits, k=10))
                if not Account.objects.filter(account_number=account_number).exists():
                    break

            account.account_number = account_number
            account.save()

            messages.success(request, f'Account {account.account_number} created successfully!')
            return redirect('banking:account_detail', account_number=account.account_number)
    else:
        form = AccountForm()

    context = {
        'form': form,
        'account_types': AccountType.objects.all(),
    }
    return render(request, 'banking/account_create.html', context)

@login_required
def account_detail(request, account_number):
    """View account details"""
    account = get_object_or_404(Account, account_number=account_number, user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-created_at')[:20]

    context = {
        'account': account,
        'transactions': transactions,
    }
    return render(request, 'banking/account_detail.html', context)

@login_required
def account_deposit(request, account_number):
    """Deposit funds into an account"""
    account = get_object_or_404(Account, account_number=account_number, user=request.user)

    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                account.deposit(amount)
                messages.success(request, f'Successfully deposited {amount} to account {account.account_number}')
                return redirect('banking:account_detail', account_number=account.account_number)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = DepositForm()

    context = {
        'form': form,
        'account': account,
    }
    return render(request, 'banking/account_deposit.html', context)

@login_required
def account_withdraw(request, account_number):
    """Withdraw funds from an account"""
    account = get_object_or_404(Account, account_number=account_number, user=request.user)

    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                account.withdraw(amount)
                messages.success(request, f'Successfully withdrew {amount} from account {account.account_number}')
                return redirect('banking:account_detail', account_number=account.account_number)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = WithdrawForm()

    context = {
        'form': form,
        'account': account,
    }
    return render(request, 'banking/account_withdraw.html', context)

@login_required
def account_transfer(request, account_number):
    """Transfer funds between accounts"""
    source_account = get_object_or_404(Account, account_number=account_number, user=request.user)

    # Get all other active accounts for this user
    destination_accounts = Account.objects.filter(
        user=request.user,
        status='active'
    ).exclude(id=source_account.id)

    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user, source_account=source_account)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            destination_account = form.cleaned_data['destination_account']

            try:
                transfer = source_account.transfer(destination_account, amount)
                messages.success(
                    request,
                    f'Successfully transferred {amount} from {source_account.account_number} to {destination_account.account_number}'
                )
                return redirect('banking:account_detail', account_number=source_account.account_number)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = TransferForm(user=request.user, source_account=source_account)

    context = {
        'form': form,
        'source_account': source_account,
        'destination_accounts': destination_accounts,
    }
    return render(request, 'banking/account_transfer.html', context)

@login_required
def account_statement(request, account_number):
    """Generate account statement"""
    account = get_object_or_404(Account, account_number=account_number, user=request.user)

    # Default to last 30 days if no date range provided
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    if request.GET.get('start_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid start date format')

    if request.GET.get('end_date'):
        try:
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid end date format')

    # Get transactions for the date range
    transactions = Transaction.objects.filter(
        account=account,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by('created_at')

    # Calculate opening and closing balances
    opening_transaction = Transaction.objects.filter(
        account=account,
        created_at__date__lt=start_date
    ).order_by('-created_at').first()

    opening_balance = opening_transaction.balance_after if opening_transaction else 0
    closing_balance = account.balance

    # Generate CSV if requested
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{account.account_number}_statement_{start_date}_to_{end_date}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Description', 'Type', 'Amount', 'Balance'])

        for transaction in transactions:
            writer.writerow([
                transaction.created_at.strftime('%Y-%m-%d %H:%M'),
                transaction.description,
                transaction.transaction_type,
                transaction.amount,
                transaction.balance_after
            ])

        return response

    # Create a statement record
    statement = Statement.objects.create(
        account=account,
        start_date=start_date,
        end_date=end_date,
        opening_balance=opening_balance,
        closing_balance=closing_balance
    )

    context = {
        'account': account,
        'transactions': transactions,
        'statement': statement,
        'start_date': start_date,
        'end_date': end_date,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
    }
    return render(request, 'banking/account_statement.html', context)

@login_required
def transaction_list(request):
    """List all transactions for the current user"""
    transactions = Transaction.objects.filter(
        account__user=request.user
    ).order_by('-created_at')

    # Filter by account if specified
    account_filter = request.GET.get('account')
    if account_filter:
        transactions = transactions.filter(account__account_number=account_filter)

    # Filter by transaction type if specified
    type_filter = request.GET.get('type')
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    # Filter by date range if specified
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            transactions = transactions.filter(created_at__date__gte=start_date)
        except ValueError:
            messages.error(request, 'Invalid start date format')

    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = transactions.filter(created_at__date__lte=end_date)
        except ValueError:
            messages.error(request, 'Invalid end date format')

    # Get all accounts for filtering
    accounts = Account.objects.filter(user=request.user)

    context = {
        'transactions': transactions,
        'accounts': accounts,
        'transaction_types': dict(Transaction.TRANSACTION_TYPES),
    }
    return render(request, 'banking/transaction_list.html', context)