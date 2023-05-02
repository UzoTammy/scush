from django import forms
from django.forms.widgets import DateInput
from core.models import JsonDataset
from .models import (BalanceSheet, 
                    TradeMonthly, 
                    TradeDaily, 
                    BankAccount, 
                    BankBalance,
                    Creditor
                    )
# from djmoney.models.fields import MoneyField, Money
from djmoney.forms import MoneyWidget, MoneyField

class TradeMonthlyForm(forms.ModelForm):
    year = forms.IntegerField(required=False)
    month = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = TradeMonthly
        fields = '__all__'

class TradeDailyForm(forms.ModelForm):
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))
    
    class Meta:
        model = TradeDaily
        fields = '__all__'

    
class BSForm(forms.ModelForm):

    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))


    class Meta:
        model = BalanceSheet
        fields = '__all__'

class BankAccountForm(forms.ModelForm):
    account_group = forms.ChoiceField(initial='Business', choices=[('Business', 'Business'), ('Admin', 'Admin')])
    bank = forms.ChoiceField(choices=[
        ('UBA', 'UBA'), ('Sterling', 'Sterling'), ('Access', 'Access'), ('Heritage', 'Heritage'),
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
    json_dict = JsonDataset.objects.get(pk=1).dataset
    SOURCES = [(i, i) for i in json_dict['product-source']]
    
    date = forms.DateField(widget=DateInput(attrs={'type':'date'}))
    account = forms.ChoiceField(choices=SOURCES)
    
    class Meta:
        model = Creditor
        fields = ['account', 'date', 'account_type', 'amount', 'ledger']

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