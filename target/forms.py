from django import forms
from .models import BudgetYear, SalesTarget, KPIBudget, KPIMonthlyTarget


class BudgetYearForm(forms.ModelForm):
    year = forms.IntegerField(
        min_value=2020,
        max_value=2040,
        widget=forms.TextInput(attrs={'type': 'number', 'min': '2020', 'max': '2040'}),
    )

    class Meta:
        model  = BudgetYear
        fields = ['year', 'sales_budget']


class SalesTargetForm(forms.ModelForm):
    class Meta:
        model  = SalesTarget
        fields = ['month', 'target']


class KPIBudgetForm(forms.ModelForm):
    class Meta:
        model  = KPIBudget
        fields = ['metric', 'annual_value']


class KPIMonthlyTargetForm(forms.ModelForm):
    class Meta:
        model  = KPIMonthlyTarget
        fields = ['month', 'metric', 'target_value']
