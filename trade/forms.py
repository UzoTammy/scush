import datetime
from decimal import Decimal
from typing import Any, Mapping

from django import forms
from django.forms.renderers import BaseRenderer
from django.forms.utils import ErrorList
from django.forms.widgets import DateInput
from core.models import JsonDataset
from .models import (BalanceSheet,
                    TradeMonthly,
                    TradeDaily,
                    BankAccount,
                    BankBalance,
                    Creditor,
                    CashProjection,
                    TradeBudget
                    )

# from djmoney.models.fields import MoneyField, Money
from djmoney.forms import MoneyField
from djmoney.money import Money

# Gross profit is allowed to diverge from (Sales - Purchase) by up to this
# fraction before an anomaly warning is raised. Accounting software may include
# adjustments (write-offs, stock corrections) that cause a legitimate divergence.
_GP_DIVERGENCE_THRESHOLD = Decimal('0.10')  # 10%


def _validate_pl(form, cleaned_data):
    """
    Shared P&L validation for daily and monthly trade forms.
    Hard blocks: impossible values (rejected outright).
    Soft anomalies: unusual but possible; require confirm_anomaly to proceed.
    """
    zero = Money(0, 'NGN')

    sales            = cleaned_data.get('sales')
    purchase         = cleaned_data.get('purchase')
    gross_profit     = cleaned_data.get('gross_profit')
    direct_expenses  = cleaned_data.get('direct_expenses')
    indirect_expenses= cleaned_data.get('indirect_expenses')
    opening_value    = cleaned_data.get('opening_value')
    closing_value    = cleaned_data.get('closing_value')
    confirm          = cleaned_data.get('confirm_anomaly', False)

    # --- Hard blocks ---
    if sales is not None and sales <= zero:
        form.add_error('sales', 'Sales must be greater than zero.')
    if purchase is not None and purchase < zero:
        form.add_error('purchase', 'Purchase cannot be negative.')
    if gross_profit is not None and gross_profit < zero:
        form.add_error('gross_profit', 'Gross profit cannot be negative.')
    if gross_profit is not None and sales is not None and sales > zero and gross_profit > sales:
        form.add_error('gross_profit', 'Gross profit cannot exceed sales.')
    if direct_expenses is not None and direct_expenses < zero:
        form.add_error('direct_expenses', 'Direct expenses cannot be negative.')
    if indirect_expenses is not None and indirect_expenses < zero:
        form.add_error('indirect_expenses', 'Indirect expenses cannot be negative.')
    if opening_value is not None and opening_value < zero:
        form.add_error('opening_value', 'Opening stock value cannot be negative.')
    if closing_value is not None and closing_value < zero:
        form.add_error('closing_value', 'Closing stock value cannot be negative.')

    # Stop here if hard errors already exist — anomaly checks on bad data are misleading.
    if form.errors:
        return cleaned_data

    # --- Soft anomalies (require explicit acknowledgement) ---
    anomalies = []

    if purchase is not None and sales is not None and purchase > sales:
        anomalies.append(
            f'Purchase ({purchase}) exceeds sales ({sales}) — cost is higher than revenue.'
        )

    if gross_profit is not None and indirect_expenses is not None:
        net_profit = gross_profit - indirect_expenses
        if net_profit < zero:
            anomalies.append(
                f'Net profit is negative ({net_profit}) — this records a net loss for the period.'
            )

    if all(v is not None for v in [sales, purchase, gross_profit]) and sales > zero:
        expected_gp = sales - purchase
        if expected_gp > zero:
            divergence = abs(gross_profit.amount - expected_gp.amount) / expected_gp.amount
            if divergence > _GP_DIVERGENCE_THRESHOLD:
                anomalies.append(
                    f'Gross profit ({gross_profit}) differs from Sales − Purchase '
                    f'({expected_gp}) by {round(100 * divergence, 1)} %. '
                    f'Verify this matches the accounting software output.'
                )

    if anomalies and not confirm:
        for msg in anomalies:
            form.add_error(None, msg)
        form.add_error(None, 'Tick “Confirm anomaly” below to acknowledge and proceed.')

    return cleaned_data


class TradeMonthlyForm(forms.ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    confirm_anomaly = forms.BooleanField(
        required=False,
        label='Confirm anomaly — I have reviewed the flagged figures and confirm they are correct.',
    )

    class Meta:
        model = TradeMonthly
        fields = '__all__'

    def clean(self):
        return _validate_pl(self, super().clean())


class TradeDailyForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))
    confirm_anomaly = forms.BooleanField(
        required=False,
        label='Confirm anomaly — I have reviewed the flagged figures and confirm they are correct.',
    )

    class Meta:
        model = TradeDaily
        fields = '__all__'

    def clean(self):
        cleaned_data = _validate_pl(self, super().clean())

        opening_value = cleaned_data.get('opening_value')
        date = cleaned_data.get('date')
        confirm = cleaned_data.get('confirm_anomaly', False)

        # Stock continuity: opening value must match prior record's closing value.
        if opening_value is not None and date is not None and 'opening_value' not in self.errors:
            prior_qs = TradeDaily.objects.filter(date__lt=date)
            if self.instance.pk:
                prior_qs = prior_qs.exclude(pk=self.instance.pk)

            if prior_qs.exists():
                prior = prior_qs.latest('date')
                if prior.closing_value != opening_value:
                    gap = opening_value - prior.closing_value
                    sign = '+' if gap.amount >= 0 else ''
                    if not confirm:
                        self.add_error(
                            'opening_value',
                            f'Stock gap: opening value ({opening_value}) does not match '
                            f'closing stock ({prior.closing_value}) from {prior.date}. '
                            f'Difference: {sign}{gap}. '
                            f'Tick "Confirm anomaly" to acknowledge and proceed.'
                        )

        return cleaned_data
 
class BSForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    class Meta:
        model = BalanceSheet
        fields = '__all__'

class BankAccountForm(forms.ModelForm):
    account_group = forms.ChoiceField(initial='Business', choices=[('Business', 'Business'), ('Admin', 'Admin')])
    bank = forms.ChoiceField(choices=[
        ('Nil', '----'), ('UBA', 'UBA'), ('Sterling', 'Sterling'), ('Access', 'Access'), ('Heritage', 'Heritage'),
    ])

    class Meta:
        model = BankAccount
        fields = ('account_name', 'nickname', 'account_number', 'bank', 'account_group')

class BankBalanceForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    class Meta:
        model = BankBalance
        fields = '__all__'

class BankBalanceCopyForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))
    
    class Meta:
        model = BankBalance
        fields = '__all__'

class CreditorAccountForm(forms.ModelForm):
    date    = forms.DateField(widget=DateInput(attrs={'type': 'date'}))
    account = forms.ChoiceField(choices=[])

    class Meta:
        model  = Creditor
        fields = ['account', 'date', 'account_type', 'amount', 'ledger']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            data    = JsonDataset.objects.filter(pk=1).first()
            sources = [(i, i) for i in data.dataset['product-source']] if data else []
        except Exception:
            sources = []
        self.fields['account'].choices = sources

class FinancialForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))

    class Meta:
        model = TradeDaily
        exclude = ('direct_income', 'indirect_income')
    
    profit = MoneyField(max_digits=13, decimal_places=2)
    liability = MoneyField(max_digits=13, decimal_places=2)
    current_asset = MoneyField(max_digits=13, decimal_places=2)
    sundry_debtor = MoneyField(max_digits=13, decimal_places=2)
    
    def save(self, commit=True):
        trade = TradeDaily.objects.latest('date')
        if trade:
            self.instance.trade_date = trade.date
            self.instance.direct_income = trade.direct_income
            self.instance.indirect_income = trade.indirect_income
            trade_instance = super().save(commit=False)
            
        balance_sheet = BalanceSheet.objects.latest('date')
        if balance_sheet:
            balance_sheet_instance = BalanceSheet(
                date=self.instance.date,
                profit=self.cleaned_data['profit'],
                adjusted_profit=balance_sheet.adjusted_profit,
                liability=self.cleaned_data['liability'],
                capital=balance_sheet.capital,
                loan_liability=balance_sheet.loan_liability,
                fixed_asset=balance_sheet.fixed_asset,
                current_asset=self.cleaned_data['current_asset'],
                investment=balance_sheet.investment,
                suspense=balance_sheet.suspense,
                difference=balance_sheet.difference,
                sundry_debtor=self.cleaned_data['sundry_debtor'],
            )
        if commit:
            pass
            # trade_instance.save()
            # balance_sheet_instance.save()
        return trade_instance, balance_sheet_instance

class TradeBudgetForm(forms.ModelForm):
    class Meta:
        model = TradeBudget
        fields = ('month', 'year', 'budgeted_sales', 'budgeted_purchase',
                  'budgeted_direct_expenses', 'budgeted_indirect_expenses',
                  'budgeted_gross_profit')


class CashProjectionForm(forms.ModelForm):
    expected_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}))

    class Meta:
        model = CashProjection
        fields = ('description', 'amount', 'expected_date', 'flow_type', 'category', 'is_recurring', 'notes')


class BankDepositForm(forms.Form):
    
    amount = MoneyField(max_digits=12, decimal_places=2)
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.exclude(nickname='Cash'), empty_label="Choose Bank Account")
    date = forms.DateField(initial=datetime.date.today() - datetime.timedelta(days=1), widget=DateInput(attrs={'type':'date'}))
