import datetime
import json
from decimal import Decimal
from django.db.models import Sum
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from djmoney.money import Money

from .models import (
    BudgetYear, SalesTarget, KPIBudget, KPIMonthlyTarget,
    MONTH_NAMES, KPI_METRIC_CHOICES, MONEY_METRICS, EXPENSE_METRICS,
)
from .forms import BudgetYearForm, SalesTargetForm, KPIBudgetForm, KPIMonthlyTargetForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_metric_actual(metric, year, month_num, trade_monthly, daily_qs):
    """Return Decimal actual value for a KPI metric, or None if no data."""
    if metric == 'gross_profit':
        if trade_monthly:
            return Decimal(str(trade_monthly.gross_profit.amount))
        r = daily_qs.aggregate(t=Sum('gross_profit'))['t']
        return Decimal(str(r)) if r else None

    if metric == 'direct_expense':
        if trade_monthly:
            return Decimal(str(trade_monthly.direct_expenses.amount))
        r = daily_qs.aggregate(t=Sum('direct_expenses'))['t']
        return Decimal(str(r)) if r else None

    if metric == 'indirect_expense':
        if trade_monthly:
            return Decimal(str(trade_monthly.indirect_expenses.amount))
        r = daily_qs.aggregate(t=Sum('indirect_expenses'))['t']
        return Decimal(str(r)) if r else None

    if metric == 'margin_pct':
        if trade_monthly:
            sales = float(trade_monthly.sales.amount)
            gp    = float(trade_monthly.gross_profit.amount)
            ie    = float(trade_monthly.indirect_expenses.amount)
        else:
            agg  = daily_qs.aggregate(s=Sum('sales'), gp=Sum('gross_profit'), ie=Sum('indirect_expenses'))
            sales, gp, ie = float(agg['s'] or 0), float(agg['gp'] or 0), float(agg['ie'] or 0)
        if sales > 0:
            return Decimal(str(round(100 * (gp - ie) / sales, 2)))
        return None

    if metric == 'growth_pct':
        from trade.models import BalanceSheet
        bs = BalanceSheet.objects.filter(date__year=year, date__month=month_num).order_by('-date').first()
        if bs:
            return Decimal(str(float(bs.growth_ratio())))
        return None

    return None


def _enrich_monthly(budget_year, monthly_qs):
    """Sales: pair each SalesTarget with actual from TradeMonthly/TradeDaily."""
    from trade.models import TradeMonthly, TradeDaily

    monthly_map = {
        obj.month: obj.sales
        for obj in TradeMonthly.objects.filter(year=budget_year.year)
    }
    rows = []
    for st in monthly_qs:
        month_name = MONTH_NAMES[st.month]
        if month_name in monthly_map:
            actual = monthly_map[month_name]
        else:
            daily_total = TradeDaily.objects.filter(
                date__year=budget_year.year, date__month=st.month
            ).aggregate(total=Sum('sales'))['total']
            actual = Money(daily_total or 0, 'NGN')
        variance = actual - st.target
        perf = round(100 * float(actual.amount) / float(st.target.amount), 1) if st.target.amount > 0 else 0
        rows.append({'st': st, 'actual': actual, 'variance': variance, 'performance': perf})
    return rows


def _build_kpi_data(budget_year):
    """
    Build KPI monthly tracking data for all non-sales KPIs.
    Returns (columns, rows) where:
      columns = [{'metric': ..., 'label': ..., 'is_money': bool}, ...]
      rows    = [{'month_name': ..., 'cells': [{'target', 'actual', 'variance',
                  'on_target', 'is_money', 'unit'}, ...]}, ...]
    """
    from trade.models import TradeMonthly, TradeDaily

    all_targets = list(
        KPIMonthlyTarget.objects.filter(budget_year=budget_year).order_by('month', 'metric')
    )
    if not all_targets:
        return [], []

    metric_order = [c[0] for c in KPI_METRIC_CHOICES]
    metrics_used = sorted(
        set(t.metric for t in all_targets),
        key=lambda m: metric_order.index(m),
    )
    months_used = sorted(set(t.month for t in all_targets))

    target_lookup = {}
    for t in all_targets:
        target_lookup.setdefault(t.month, {})[t.metric] = {'value': t.target_value, 'pk': t.pk}

    trade_monthly_map = {
        obj.month: obj
        for obj in TradeMonthly.objects.filter(year=budget_year.year)
    }

    columns = [
        {
            'metric':   m,
            'label':    dict(KPI_METRIC_CHOICES)[m],
            'is_money': m in MONEY_METRICS,
            'unit':     '₦' if m in MONEY_METRICS else '%',
        }
        for m in metrics_used
    ]

    rows = []
    for month_num in months_used:
        month_name  = MONTH_NAMES[month_num]
        trade_m     = trade_monthly_map.get(month_name)
        daily_qs    = (
            TradeDaily.objects.filter(date__year=budget_year.year, date__month=month_num)
            if trade_m is None else None
        )

        cells = []
        for col in columns:
            metric     = col['metric']
            entry      = target_lookup.get(month_num, {}).get(metric)
            target     = entry['value'] if entry else None
            target_pk  = entry['pk']   if entry else None
            actual     = _get_metric_actual(metric, budget_year.year, month_num, trade_m, daily_qs)
            variance   = on_target = None
            if actual is not None and target is not None:
                if metric in EXPENSE_METRICS:
                    signed = round(float(target) - float(actual), 2)
                else:
                    signed = round(float(actual) - float(target), 2)
                on_target = signed >= 0
                variance  = abs(signed)
            cells.append({
                'target':    target,
                'target_pk': target_pk,
                'actual':    actual,
                'variance':  variance,
                'on_target': on_target,
                'is_money':  col['is_money'],
                'unit':      col['unit'],
            })

        rows.append({'month_num': month_num, 'month_name': month_name, 'cells': cells})

    return columns, rows


# ---------------------------------------------------------------------------
# Sales target views
# ---------------------------------------------------------------------------

class TargetHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'target/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()

        try:
            budget_year = BudgetYear.objects.get(year=today.year)
            monthly_qs  = budget_year.monthly_targets.order_by('month')
            rows        = _enrich_monthly(budget_year, monthly_qs)
            months_set  = {st.month for st in monthly_qs}
            kpi_cols, kpi_rows = _build_kpi_data(budget_year)

            context.update({
                'budget_year':      budget_year,
                'monthly_rows':     rows,
                'months_remaining': [m for m in range(1, 13) if m not in months_set],
                'kpi_budgets':      budget_year.kpi_budgets.all(),
                'kpi_columns':      kpi_cols,
                'kpi_rows':         kpi_rows,
                'chart_labels':     json.dumps([r['st'].get_month_display()[:3] for r in rows]),
                'chart_targets':    json.dumps([float(r['st'].target.amount) for r in rows]),
                'chart_achieved':   json.dumps([float(r['actual'].amount) for r in rows]),
            })
        except BudgetYear.DoesNotExist:
            context['budget_year'] = None

        context['all_budget_years']   = BudgetYear.objects.all()
        context['current_year']        = today.year
        context['current_year_plain']  = str(today.year)
        return context


class BudgetYearListView(LoginRequiredMixin, ListView):
    model = BudgetYear
    template_name = 'target/budget_year_list.html'


class BudgetYearDetailView(LoginRequiredMixin, DetailView):
    model = BudgetYear
    template_name = 'target/budget_year_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_year = self.object
        monthly_qs  = budget_year.monthly_targets.order_by('month')
        months_set  = {st.month for st in monthly_qs}
        rows        = _enrich_monthly(budget_year, monthly_qs)
        kpi_cols, kpi_rows = _build_kpi_data(budget_year)
        context.update({
            'monthly_rows':     rows,
            'months_remaining': [m for m in range(1, 13) if m not in months_set],
            'kpi_budgets':      budget_year.kpi_budgets.all(),
            'kpi_columns':      kpi_cols,
            'kpi_rows':         kpi_rows,
            'chart_labels':     json.dumps([r['st'].get_month_display()[:3] for r in rows]),
            'chart_targets':    json.dumps([float(r['st'].target.amount) for r in rows]),
            'chart_achieved':   json.dumps([float(r['actual'].amount) for r in rows]),
        })
        return context


class BudgetYearCreateView(LoginRequiredMixin, CreateView):
    model      = BudgetYear
    form_class = BudgetYearForm
    template_name = 'target/budget_year_form.html'


class BudgetYearUpdateView(LoginRequiredMixin, UpdateView):
    model      = BudgetYear
    form_class = BudgetYearForm
    template_name = 'target/budget_year_form.html'


class SalesTargetCreateView(LoginRequiredMixin, CreateView):
    model      = SalesTarget
    form_class = SalesTargetForm
    template_name = 'target/sales_target_form.html'

    def get_budget_year(self):
        return get_object_or_404(BudgetYear, pk=self.kwargs['year_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.get_budget_year()
        return context

    def form_valid(self, form):
        form.instance.budget_year = self.get_budget_year()
        return super().form_valid(form)


class SalesTargetUpdateView(LoginRequiredMixin, UpdateView):
    model      = SalesTarget
    form_class = SalesTargetForm
    template_name = 'target/sales_target_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.object.budget_year
        return context


# ---------------------------------------------------------------------------
# KPI budget views (annual)
# ---------------------------------------------------------------------------

class KPIBudgetCreateView(LoginRequiredMixin, CreateView):
    model      = KPIBudget
    form_class = KPIBudgetForm
    template_name = 'target/kpi_budget_form.html'

    def get_budget_year(self):
        return get_object_or_404(BudgetYear, pk=self.kwargs['year_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.get_budget_year()
        return context

    def form_valid(self, form):
        form.instance.budget_year = self.get_budget_year()
        return super().form_valid(form)


class KPIBudgetUpdateView(LoginRequiredMixin, UpdateView):
    model      = KPIBudget
    form_class = KPIBudgetForm
    template_name = 'target/kpi_budget_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.object.budget_year
        return context


# ---------------------------------------------------------------------------
# KPI monthly target views
# ---------------------------------------------------------------------------

class KPIMonthlyTargetCreateView(LoginRequiredMixin, CreateView):
    model      = KPIMonthlyTarget
    form_class = KPIMonthlyTargetForm
    template_name = 'target/kpi_monthly_target_form.html'

    def get_budget_year(self):
        return get_object_or_404(BudgetYear, pk=self.kwargs['year_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.get_budget_year()
        return context

    def form_valid(self, form):
        form.instance.budget_year = self.get_budget_year()
        return super().form_valid(form)


class KPIMonthlyTargetUpdateView(LoginRequiredMixin, UpdateView):
    model      = KPIMonthlyTarget
    form_class = KPIMonthlyTargetForm
    template_name = 'target/kpi_monthly_target_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_year'] = self.object.budget_year
        return context
