from django import forms
from .models import Account, AccountType

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['account_type', 'currency', 'nickname']
        widgets = {
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional nickname for this account'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account_type'].queryset = AccountType.objects.all()
        self.fields['account_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['currency'].widget.attrs.update({'class': 'form-control'})

class DepositForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01, 
        max_digits=12, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to deposit'})
    )

class WithdrawForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01, 
        max_digits=12, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to withdraw'})
    )

class TransferForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01, 
        max_digits=12, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to transfer'})
    )
    destination_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        source_account = kwargs.pop('source_account', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Only show active accounts that belong to the user and are not the source account
            self.fields['destination_account'].queryset = Account.objects.filter(
                user=user, 
                status='active'
            ).exclude(id=source_account.id if source_account else None)
