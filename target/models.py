import datetime
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from django.urls import reverse
from django.core.validators import MaxValueValidator, MinValueValidator

MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
    (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
    (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
]

_YEAR_VALIDATORS = [MinValueValidator(2020), MaxValueValidator(2040)]

MONTH_NAMES = {i: datetime.date(2000, i, 1).strftime('%B') for i in range(1, 13)}

KPI_METRIC_CHOICES = [
    ('gross_profit',    'Gross Profit'),
    ('direct_expense',  'Direct Expenses'),
    ('indirect_expense','Indirect Expenses'),
    ('margin_pct',      'Margin %'),
    ('growth_pct',      'Growth %'),
]

MONEY_METRICS   = frozenset({'gross_profit', 'direct_expense', 'indirect_expense'})
RATIO_METRICS   = frozenset({'margin_pct', 'growth_pct'})
EXPENSE_METRICS = frozenset({'direct_expense', 'indirect_expense'})


class BudgetYear(models.Model):
    year = models.PositiveSmallIntegerField(
        unique=True,
        default=datetime.date.today().year,
        validators=_YEAR_VALIDATORS,
    )
    sales_budget = MoneyField(max_digits=14, default_currency='NGN', decimal_places=2)

    class Meta:
        ordering = ['-year']
        verbose_name = 'Budget Year'

    def __str__(self):
        return f'{self.year} Budget'

    def get_absolute_url(self):
        return reverse('budget-year-detail', kwargs={'pk': self.pk})

    def total_target(self):
        result = self.monthly_targets.aggregate(total=Sum('target'))['total']
        return Money(result or 0, 'NGN')

    def total_achieved(self):
        from trade.models import TradeMonthly, TradeDaily
        month_nums = list(self.monthly_targets.values_list('month', flat=True))
        month_names = [MONTH_NAMES[m] for m in month_nums]
        monthly_map = {
            obj.month: obj.sales.amount
            for obj in TradeMonthly.objects.filter(year=self.year, month__in=month_names)
        }
        total = Decimal('0')
        for num, name in zip(month_nums, month_names):
            if name in monthly_map:
                total += monthly_map[name]
            else:
                daily = TradeDaily.objects.filter(
                    date__year=self.year, date__month=num
                ).aggregate(s=Sum('sales'))['s']
                total += daily or Decimal('0')
        return Money(total, 'NGN')

    def budget_coverage(self):
        if self.sales_budget.amount > 0:
            return round(100 * float(self.total_target().amount) / float(self.sales_budget.amount), 1)
        return 0

    def budget_achievement(self):
        if self.sales_budget.amount > 0:
            return round(100 * float(self.total_achieved().amount) / float(self.sales_budget.amount), 1)
        return 0


class SalesTarget(models.Model):
    budget_year = models.ForeignKey(
        BudgetYear, on_delete=models.CASCADE, related_name='monthly_targets')
    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    target = MoneyField(max_digits=14, default_currency='NGN', decimal_places=2)

    class Meta:
        unique_together = [('budget_year', 'month')]
        ordering = ['budget_year__year', 'month']
        verbose_name = 'Monthly Sales Target'

    def __str__(self):
        return f'{self.get_month_display()} {self.budget_year.year}'

    def get_absolute_url(self):
        return reverse('budget-year-detail', kwargs={'pk': self.budget_year_id})


class KPIBudget(models.Model):
    """Annual budget / ceiling for a single KPI metric."""
    budget_year  = models.ForeignKey(BudgetYear, on_delete=models.CASCADE, related_name='kpi_budgets')
    metric       = models.CharField(max_length=20, choices=KPI_METRIC_CHOICES)
    annual_value = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        unique_together = [('budget_year', 'metric')]
        ordering = ['metric']
        verbose_name = 'KPI Annual Budget'

    def __str__(self):
        return f'{self.get_metric_display()} — {self.budget_year.year}'

    def get_absolute_url(self):
        return reverse('budget-year-detail', kwargs={'pk': self.budget_year_id})

    def is_money(self):
        return self.metric in MONEY_METRICS

    def unit(self):
        return '₦' if self.is_money() else '%'


class KPIMonthlyTarget(models.Model):
    """Monthly target for a single KPI metric."""
    budget_year  = models.ForeignKey(BudgetYear, on_delete=models.CASCADE, related_name='kpi_monthly_targets')
    month        = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    metric       = models.CharField(max_length=20, choices=KPI_METRIC_CHOICES)
    target_value = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        unique_together = [('budget_year', 'month', 'metric')]
        ordering = ['budget_year__year', 'month', 'metric']
        verbose_name = 'KPI Monthly Target'

    def __str__(self):
        return f'{self.get_metric_display()} — {self.get_month_display()} {self.budget_year.year}'

    def get_absolute_url(self):
        return reverse('budget-year-detail', kwargs={'pk': self.budget_year_id})
