import base64
import calendar
import datetime
from decimal import Decimal
import io
import itertools as it
from typing import Any
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import (LoginRequiredMixin, UserPassesTestMixin)
from django.db.models.expressions import Func
from django.db.models.fields import FloatField
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls.base import reverse_lazy
from django.db.models import (Sum, F, Avg, ExpressionWrapper, DecimalField, Value)
from django.views.generic import (TemplateView, CreateView, ListView, DetailView, UpdateView, FormView, View)                            

from djmoney.money import Money
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from ozone import mytools
from core import utils as plotter
from stock.models import ProductExtension
from .forms import (BSForm, TradeMonthlyForm, TradeDailyForm, BankAccountForm, BankBalanceForm,
                    BankBalanceCopyForm, CreditorAccountForm, FinancialForm, BankDepositForm,
                    CashProjectionForm)
from .models import (TradeDaily, TradeMonthly, BalanceSheet, BankAccount, BankBalance,
                     Creditor, TradeAuditLog, TradeAdjustmentRequest, CashProjection)


def _capture_changes(form):
    """Return {field: {old, new}} for every field whose value changed on an update form."""
    changes = {}
    for field_name, new_value in form.cleaned_data.items():
        if field_name in ('confirm_anomaly',) or field_name.endswith('_currency'):
            continue
        old_value = form.initial.get(field_name)
        old_str = str(old_value) if old_value is not None else ''
        new_str = str(new_value) if new_value is not None else ''
        if old_str != new_str:
            changes[field_name] = {'old': old_str, 'new': new_str}
    return changes


def _growth_pct(current, previous):
    """Return % change from previous to current, or None if previous is zero."""
    try:
        prev = float(previous)
        if not prev:
            return None
        return round(100 * (float(current) / prev - 1), 1)
    except (TypeError, ZeroDivisionError):
        return None


def _build_kpi_comparison(year, month_num, actual_margin, actual_lc, actual_ac, actual_growth=None):
    """Return a structured target-vs-actual KPI list for the given period, or None if no target exists."""
    from target.models import PositionKPIMonthly
    qs = PositionKPIMonthly.objects.filter(year=year, month=month_num)
    if not qs.exists():
        return None
    kpi = qs.first()
    items = [
        {'name': 'Gross Margin',   'target': kpi.margin,   'actual': round(float(actual_margin), 2), 'higher_is_better': True},
        {'name': 'Landing Cost',   'target': kpi.delivery, 'actual': round(float(actual_lc), 2),     'higher_is_better': False},
        {'name': 'Admin Cost',     'target': kpi.admin,    'actual': round(float(actual_ac), 2),     'higher_is_better': False},
    ]
    if actual_growth is not None:
        items.append({'name': 'Growth', 'target': kpi.growth, 'actual': round(float(actual_growth), 2), 'higher_is_better': True})
    for item in items:
        item['gap'] = round(item['actual'] - item['target'], 2)
        item['on_target'] = item['actual'] >= item['target'] if item['higher_is_better'] else item['actual'] <= item['target']
    return {'items': items, 'period': str(kpi)}


def _capture_proposed_changes(form):
    """Like _capture_changes but stores type metadata so changes can be applied later."""
    changes = {}
    for field_name, new_value in form.cleaned_data.items():
        if field_name in ('confirm_anomaly',) or field_name.endswith('_currency'):
            continue
        old_value = form.initial.get(field_name)
        if str(old_value) == str(new_value):
            continue
        if hasattr(new_value, 'amount') and hasattr(new_value, 'currency'):
            new_data = {'type': 'money', 'amount': str(new_value.amount), 'currency': str(new_value.currency)}
        elif isinstance(new_value, datetime.date):
            new_data = {'type': 'date', 'value': new_value.isoformat()}
        elif isinstance(new_value, bool):
            new_data = {'type': 'bool', 'value': new_value}
        elif isinstance(new_value, int):
            new_data = {'type': 'int', 'value': new_value}
        else:
            new_data = {'type': 'str', 'value': str(new_value) if new_value is not None else ''}
        changes[field_name] = {
            'old_display': str(old_value) if old_value is not None else '',
            'new_display': str(new_value) if new_value is not None else '',
            'new_data': new_data,
        }
    return changes


def _apply_proposed_changes(instance, proposed_changes):
    """Apply type-aware proposed changes to a model instance and save."""
    for field_name, change in proposed_changes.items():
        nd = change['new_data']
        if nd['type'] == 'money':
            value = Money(Decimal(nd['amount']), nd['currency'])
        elif nd['type'] == 'date':
            value = datetime.date.fromisoformat(nd['value'])
        elif nd['type'] == 'bool':
            value = bool(nd['value'])
        elif nd['type'] == 'int':
            value = int(nd['value'])
        else:
            try:
                model_field = instance._meta.get_field(field_name)
                value = model_field.to_python(nd['value'])
            except Exception:
                value = nd['value']
        setattr(instance, field_name, value)
    instance.save()


def _log_update(request, instance, changes):
    if changes:
        TradeAuditLog.objects.create(
            model_name=type(instance).__name__,
            record_id=instance.pk,
            record_str=str(instance),
            user=request.user,
            changes=changes,
        )


GROUP_NAME = 'Administrator'

# Any bank account whose |delta| exceeds this amount triggers a visible alert.
# Adjust as the business tolerance changes.
BANK_DELTA_THRESHOLD = Decimal('1000')

class EmailSample(TemplateView):
    template_name = 'mail/sample.html'


class TradeHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView): 
    template_name = 'trade/home.html'

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False
    
    def quarter_group(self, queryset, year, quarter):
        qs_list = list()
        for month in quarter:
            qs_list.append(queryset.filter(year=year, month=month))
        
        qs_union = qs_list[0]|qs_list[1]|qs_list[2]
        sales, purchase, direct, indirect, gp = 0, 0, 0, 0, 0
        
        for obj in qs_union:
            sales += obj.sales.amount
            purchase += obj.purchase.amount
            direct += obj.direct_expenses.amount
            indirect += obj.indirect_expenses.amount
            gp += obj.gp_ratio
        return sales, purchase, direct, indirect, gp, qs_union.count()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        daily_qs = TradeDaily.objects.all()  #.annotate(gp_ratio=ExpressionWrapper(F('gross_profit'), output_field=DecimalField()))
        if daily_qs.exists():
            daily_qs = daily_qs.annotate(expenses=F('direct_expenses')+F('indirect_expenses'))
            daily_qs = daily_qs.annotate(net_profit=F('gross_profit')-F('indirect_expenses'))
            
            daily = daily_qs.latest('date')
            
            year = daily.date.year
            month = daily.date.month
            context['month_string'] = mytools.Period.full_months[str(month).zfill(2)]
            
            # get the queryset before you go for the month
            qs_for_chart =  daily_qs.order_by('-date')[:5]
            
            daily_qs = daily_qs.filter(date__year=year, date__month=month)

            context['daily_monthly'] = {
                'opening_stock': daily_qs.earliest('date').opening_value,
                "sales": daily_qs.aggregate(Sum('sales'))['sales__sum'],
                "indirect_expenses": daily_qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'],
                "direct_income": daily_qs.aggregate(Sum('indirect_income'))['indirect_income__sum'],
                "indirect_income": daily_qs.aggregate(Sum('direct_income'))['direct_income__sum'],
                "direct_expenses": daily_qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'],
                "gross_profit": daily_qs.aggregate(Sum('gross_profit'))['gross_profit__sum'],
                "net_profit": daily_qs.aggregate(Sum('net_profit'))['net_profit__sum'],
                "expenses": daily_qs.aggregate(Sum('expenses'))['expenses__sum'],
                "purchase": daily_qs.aggregate(Sum('purchase'))['purchase__sum'],  
            }
            context['year'] = f'{year}'
            context['month'] = month
            context['daily'] = daily
            context['object'] = BalanceSheet.objects.latest('date') 

            # The Sales Drive Ratio: Sales by opening stock
            dates = [x.date.strftime('%d-%m-%Y') for x in qs_for_chart]
            sales = [round(100*y.sales/y.opening_value, 2) for y in qs_for_chart]
            dates.reverse()
            sales.reverse()
            context['chart'] = plotter.sales_stock_figure(dates, sales)
        if self.request.user.is_superuser:
            context['pending_adjustments'] = TradeAdjustmentRequest.objects.filter(
                status=TradeAdjustmentRequest.STATUS_PENDING
            ).count()
        if daily_qs.exists():
            dm = context.get('daily_monthly', {})
            def _safe_pct(num, den):
                try:
                    n = num.amount if hasattr(num, 'amount') else float(num or 0)
                    d = den.amount if hasattr(den, 'amount') else float(den or 0)
                    return round(100 * n / d, 2) if d else 0
                except Exception:
                    return 0
            actual_margin = _safe_pct(dm.get('net_profit', 0), dm.get('sales', 0))
            actual_lc     = _safe_pct(dm.get('indirect_expenses', 0), dm.get('purchase', 0))
            actual_ac     = _safe_pct(dm.get('direct_expenses', 0), dm.get('sales', 0))
            bs_qs = BalanceSheet.objects.filter(date__year=year, date__month=month)
            actual_growth = float(bs_qs.latest('date').growth_ratio()) if bs_qs.exists() else None
            context['kpi_data'] = _build_kpi_comparison(year, month, actual_margin, actual_lc, actual_ac, actual_growth)
        if Creditor.objects.exists():
            zero = Money(0, 'NGN')
            cr_sum = sum(
                (obj.amount for obj in Creditor.objects.filter(ledger='CR')), zero
            )
            dr_sum = sum(
                (obj.amount for obj in Creditor.objects.filter(ledger='DR')), zero
            )
            outstanding = cr_sum - dr_sum
            if outstanding > zero:
                context['creditor_outstanding'] = outstanding
        return context
  

class TradeMonthlyCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TradeMonthly
    form_class = TradeMonthlyForm
    success_url = reverse_lazy('trade-home')
    

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add'

        if self.get_queryset().exists():
            context['queryset_exist'] = True
            last_record_year = self.get_queryset().last().year
            last_record_month = self.get_queryset().last().month
            
            tuple_month = tuple(calendar.month_name)
            for i in tuple_month:
                if i == last_record_month:
                    num = tuple_month.index(i)
            
            if num == 12:
                num = 1
                last_record_year += 1  
            else:
                num += 1
                
            context['last_record'] = {'year': last_record_year, 'month': tuple_month[num]}
        else: 
            context['query_set'] = False 
        return context

    
    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        form.instance.year = context['last_record']['year']
        form.instance.month = context['last_record']['month']
        return super().form_valid(form)


class TradeMonthlyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = TradeMonthly

    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = kwargs['object']
        
        context['net_profit'] = obj.gross_profit-obj.indirect_expenses
        context['margin_ratio'] = round(100*(obj.gross_profit-obj.indirect_expenses)/obj.sales, 2)
        context['delivery_ratio'] = round(100*obj.direct_expenses/obj.sales, 2)
        context['admin_ratio'] = round(100*obj.indirect_expenses/obj.sales, 2)
        return context


class TradeMonthlyListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeMonthly
    
    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_queryset(self):
        pl = TradeMonthly.objects.last()
        year = pl.year 
        return super().get_queryset().filter(year=year).order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        latest_date = TradeDaily.objects.latest('date').date
        qs = TradeDaily.objects.filter(date__year=latest_date.year).filter(date__month=latest_date.month)
        # final_obj = TradeDaily.objects.latest('date')
        if qs.exists():
            pl_obj = {
                'month': latest_date.strftime('%B, %Y'),
                'opening_stock': qs.earliest('date').opening_value,
                'sales': Money(qs.aggregate(Sum('sales'))['sales__sum'], 'NGN'),
                'purchase': Money(qs.aggregate(Sum('purchase'))['purchase__sum'], 'NGN'),
                'direct_expenses': Money(qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'], 'NGN'),  
                'indirect_expenses': Money(qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'], 'NGN'),
                'closing_stock': qs.latest('date').closing_value,
                'gross_profit': Money(qs.aggregate(Sum('gross_profit'))['gross_profit__sum'], 'NGN')
            }
            context['current_pl'] = pl_obj
            month = [obj.month for obj in self.get_queryset().order_by('pk')]
            month.append(latest_date.strftime('%B'))
            sales = [obj.sales.amount for obj in self.get_queryset().order_by('pk')]
            sales.append(pl_obj['sales'].amount)    
            context['chart'] = plotter.monthly_sales_revenue(month, sales)
        
        latest = TradeMonthly.objects.last()
        latest_year = latest.year
        trade = TradeMonthly.objects.filter(year=latest_year - 2)

        if not trade.exists():
            latest_month = latest.month
            current_year_trade = TradeMonthly.objects.filter(year=latest_year)
            current_year_trade_size = current_year_trade.count()

            trade_data = [
                trade for trade in it.zip_longest(
                ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[:current_year_trade_size],
                TradeMonthly.objects.filter(year=latest_year-2).filter(month__lte=latest_month),
                TradeMonthly.objects.filter(year=latest_year-1).filter(month__lte=latest_month),
                current_year_trade
                )]
            
            first_year = TradeMonthly.objects.filter(year=latest_year-2)
            second_year = TradeMonthly.objects.filter(year=latest_year-1)
            current_year = TradeMonthly.objects.filter(year=latest_year)

            context['years'] = (str(latest_year-2), str(latest_year-1), str(latest_year))
            context['monthly_trade'] = trade_data
            sy_gp  = second_year.aggregate(Sum('gross_profit'))['gross_profit__sum'] or Decimal('0')
            cy_gp  = current_year.aggregate(Sum('gross_profit'))['gross_profit__sum'] or Decimal('0')
            fy_gp  = first_year.aggregate(Sum('gross_profit'))['gross_profit__sum']   or Decimal('0')
            context['sum_monthly_trade'] = {
                'first_year':   Money(fy_gp, 'NGN'),
                'second_year':  Money(sy_gp, 'NGN'),
                'current_year': Money(cy_gp, 'NGN'),
                'yoy_fy_sy':  _growth_pct(sy_gp, fy_gp),
                'yoy_sy_cy':  _growth_pct(cy_gp, sy_gp),
            }

        # MoM and YoY growth per monthly record
        records_asc = list(TradeMonthly.objects.filter(year=latest_year).order_by('pk'))
        growth = {}
        for i, rec in enumerate(records_asc):
            net_p = rec.gross_profit.amount - rec.indirect_expenses.amount
            mom_s = mom_n = yoy_s = yoy_n = None
            if i > 0:
                prev = records_asc[i - 1]
                prev_np = prev.gross_profit.amount - prev.indirect_expenses.amount
                mom_s = _growth_pct(rec.sales.amount, prev.sales.amount)
                mom_n = _growth_pct(net_p, prev_np)
            prior = TradeMonthly.objects.filter(year=latest_year - 1, month=rec.month).first()
            if prior:
                prior_np = prior.gross_profit.amount - prior.indirect_expenses.amount
                yoy_s = _growth_pct(rec.sales.amount, prior.sales.amount)
                yoy_n = _growth_pct(net_p, prior_np)
            growth[rec.pk] = {'mom_sales': mom_s, 'mom_np': mom_n, 'yoy_sales': yoy_s, 'yoy_np': yoy_n}

        context['growth_list'] = [(obj, growth.get(obj.pk, {})) for obj in self.get_queryset()]
        return context


class TradeMonthlyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TradeMonthly
    form_class = TradeMonthlyForm

    def test_func(self):
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.locked:
            messages.error(request, f'{obj} is locked and cannot be edited. Contact a superuser to unlock it.')
            return redirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            proposed = _capture_proposed_changes(form)
            if proposed:
                TradeAdjustmentRequest.objects.create(
                    model_name=self.model.__name__,
                    record_id=self.object.pk,
                    record_str=str(self.object),
                    requester=self.request.user,
                    proposed_changes=proposed,
                )
                messages.info(self.request, 'Your adjustment has been submitted for superuser approval.')
                return redirect(self.object.get_absolute_url())
            return redirect(self.object.get_absolute_url())
        changes = _capture_changes(form)
        response = super().form_valid(form)
        _log_update(self.request, self.object, changes)
        return response


class TradeTradingReport(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    df = 10_000 # decimal factor
    template_name = 'trade/trading_account.html'

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False
    
    def get(self, request, *args, **kwargs):
        
        context = dict()
        naira = chr(8358)

        if request.GET == {}:
            current_year = datetime.date.today().year
        else:
            current_year = datetime.date(int(request.GET['year']), 1, 1).year
        
        monthly_trade = TradeMonthly.objects.filter(year=current_year)
        
        context['monthly'] = str(current_year)
        context['available_years'] = (
            TradeMonthly.objects.values_list('year', flat=True).distinct().order_by('-year')
        )

        if monthly_trade.exists():
        
            """Adding derivatives: direct expenses, net Profit, percent margin"""
                    
            qs = monthly_trade.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
                    
            qs = qs.annotate(net_profit=(F('gross_profit') - F('indirect_expenses')))

            template = '%(function)s(%(expressions)s AS FLOAT)'

            gp   = Func(F('gross_profit'), function='CAST', template=template)
            ide  = Func(F('gross_profit'), function='CAST', template=template)
            raw_sales = Func(F('sales'), function='CAST', template=template)

            # Wrap every denominator with NULLIF so zero-value records return NULL
            # instead of raising a database division-by-zero error.
            safe_sales    = Func(raw_sales, Value(0.0), function='NULLIF')
            safe_gp       = Func(F('gross_profit'), Value(0), function='NULLIF')
            safe_purchase = Func(F('purchase'),     Value(0), function='NULLIF')
            safe_trade_base = Func(F('purchase') + F('sales'), Value(0), function='NULLIF')

            qs = qs.annotate(gross_margin_ratio=ExpressionWrapper(
                100 * self.df * gp / safe_sales, output_field=FloatField()))
            qs = qs.annotate(sales_ratio=ExpressionWrapper(
                100 * self.df * ide / safe_sales, output_field=FloatField()))
            qs = qs.annotate(gross_ratio=ExpressionWrapper(
                100 * self.df * (F('indirect_expenses') + F('direct_expenses')) / safe_gp,
                output_field=DecimalField()))
            qs = qs.annotate(purchase_ratio=ExpressionWrapper(
                100 * self.df * F('indirect_expenses') / safe_purchase,
                output_field=DecimalField()))
            qs = qs.annotate(trade_ratio=ExpressionWrapper(
                100 * self.df * F('expenses') / safe_trade_base,
                output_field=DecimalField()))
            # qs.exclude(sales=Money(0, 'NGN'))
            qs.order_by('id')
                
            period = monthly_trade.values_list('month', flat=True)
            period_label = list(i[0:3] for i in period)
            sales = monthly_trade.values_list('sales', flat=True)

            current_month_qs = qs.order_by('pk').last()
            current_month = current_month_qs.month

            first_record = qs.filter(month='January').first() or qs.order_by('pk').first()

            current_year_total = {
                'heading': f"Current Year Total ({naira}) as at {current_month}, {current_year}",
                'opening_stock': first_record.opening_value,
                'purchase': qs.aggregate(total=Sum('purchase'))['total'],
                'direct_expenses': qs.aggregate(total=Sum('direct_expenses'))['total'],
                'gross_profit': qs.aggregate(total=Sum('gross_profit'))['total'],

                'first_total': first_record.opening_value.amount +
                qs.aggregate(total=Sum('purchase'))['total'] +
                qs.aggregate(total=Sum('direct_expenses'))['total'] +
                qs.aggregate(total=Sum('gross_profit'))['total'],
                
                'sales': qs.aggregate(total=Sum('sales'))['total'],
                'direct_income': qs.aggregate(total=Sum('direct_income'))['total'],
                'closing_stock': qs.last().closing_value.amount,
                
                'second_total': qs.last().closing_value.amount + 
                qs.aggregate(total=Sum('sales'))['total'] + 
                qs.aggregate(total=Sum('direct_income'))['total'], 
                
                'indirect_expenses': qs.aggregate(total=Sum('indirect_expenses'))['total'],
                'net_profit': qs.aggregate(total=Sum('net_profit'))['total'],
                'indirect_income': qs.aggregate(total=Sum('indirect_income'))['total'],
                
                'percent_margin': qs.aggregate(total=Avg('gross_margin_ratio'))['total']/self.df,
                'percent_sales': qs.aggregate(total=Avg('sales_ratio'))['total']/self.df,
                'percent_gross': qs.aggregate(total=Avg('gross_ratio'))['total']/self.df,
                'percent_purchase': qs.aggregate(total=Avg('purchase_ratio'))['total']/self.df,

                'expenses': qs.aggregate(total=Sum('expenses'))['total'],
                }
            
            if qs.count() >= 2:
                previous_month_qs = qs.order_by('pk').filter(pk__lt=current_month_qs.pk).last()

                previous_month = {
                'heading': f'Previous Month {previous_month_qs.month} ({naira})',
                'opening_stock': previous_month_qs.opening_value,
                'purchase': previous_month_qs.purchase.amount,
                'direct_expenses': previous_month_qs.direct_expenses.amount,
                'gross_profit': previous_month_qs.gross_profit.amount,

                'first_total':  previous_month_qs.opening_value.amount + 
                previous_month_qs.purchase.amount + 
                previous_month_qs.direct_expenses.amount + 
                previous_month_qs.gross_profit.amount,
                
                'sales': previous_month_qs.sales.amount,
                'direct_income': previous_month_qs.direct_income.amount,
                'closing_stock': previous_month_qs.closing_value.amount,

                'second_total':previous_month_qs.sales.amount + 
                previous_month_qs.direct_income.amount + 
                previous_month_qs.closing_value.amount,

                'indirect_expenses': previous_month_qs.indirect_expenses.amount,
                'net_profit': previous_month_qs.net_profit,
                'indirect_income': previous_month_qs.indirect_income.amount,
                
                'percent_margin': previous_month_qs.gross_margin_ratio/self.df,
                'percent_sales': previous_month_qs.sales_ratio/self.df,
                'percent_gross': previous_month_qs.gross_ratio/self.df,
                'percent_purchase': previous_month_qs.purchase_ratio/self.df,

                'expenses': previous_month_qs.expenses,
                }
        
                current_month = {
                    'heading': f'Current Month {current_month} ({naira})',
                    'opening_stock': current_month_qs.opening_value,
                    'purchase': current_month_qs.purchase.amount,
                    'direct_expenses': current_month_qs.direct_expenses.amount,
                    'gross_profit': current_month_qs.gross_profit.amount,

                    'first_total':  current_month_qs.opening_value.amount + 
                    current_month_qs.purchase.amount + 
                    current_month_qs.direct_expenses.amount + 
                    current_month_qs.gross_profit.amount,
                    
                    'sales': current_month_qs.sales.amount,
                    'direct_income': current_month_qs.direct_income.amount,
                    'closing_stock': current_month_qs.closing_value.amount,

                    'second_total':current_month_qs.sales.amount + 
                    current_month_qs.direct_income.amount + 
                    current_month_qs.closing_value.amount,

                    'indirect_expenses': current_month_qs.indirect_expenses.amount,
                    'net_profit': current_month_qs.net_profit,
                    'indirect_income': current_month_qs.indirect_income.amount,
                    
                    'percent_margin': current_month_qs.gross_margin_ratio/self.df,
                    'percent_sales': current_month_qs.sales_ratio/self.df,
                    'percent_gross': current_month_qs.gross_ratio/self.df,
                    'percent_purchase': current_month_qs.purchase_ratio/self.df,
                    
                    'expenses': current_month_qs.expenses,
                    
                    }
                
                
                context['np_percent'] = round(100 * (current_month['net_profit']/previous_month['net_profit'] - 1), 3)
                # context['np_bool'] = current_month['net_profit'] > previous_month['net_profit']
                
                context['expense_value'] = current_month['expenses'] - previous_month['expenses']
                context['expense_bool'] = current_month['expenses'] > previous_month['expenses']
                
                context['lc_ratio'] = 100*(current_month['indirect_expenses']/current_month['purchase']) # landing cost ratio
                context['ac_ratio'] = 100*(current_month['direct_expenses']/current_month['sales']) # administrative cost ratio
                context['gp_ratio'] = current_month.get('percent_margin')

                # KPI target vs actual
                month_to_num = {name: num for num, name in enumerate(calendar.month_name) if name}
                current_month_num = month_to_num.get(current_month_qs.month, 0)
                bs_qs = BalanceSheet.objects.filter(date__year=current_year, date__month=current_month_num)
                actual_growth = float(bs_qs.latest('date').growth_ratio()) if bs_qs.exists() else None
                context['kpi_data'] = _build_kpi_comparison(
                    current_year, current_month_num,
                    context['gp_ratio'], context['lc_ratio'], context['ac_ratio'], actual_growth
                )

                context['recordset'] = (previous_month, current_month, current_year_total)
                context['dataset'] = qs.order_by('pk')

                # YoY summary — compare current year totals against prior year
                prior_year_qs = TradeMonthly.objects.filter(year=current_year - 1)
                if prior_year_qs.exists():
                    cy_sales = qs.aggregate(total=Sum('sales'))['total'] or Decimal('0')
                    cy_gp    = qs.aggregate(total=Sum('gross_profit'))['total'] or Decimal('0')
                    cy_np    = sum(o.gross_profit.amount - o.indirect_expenses.amount for o in qs)
                    py_sales = prior_year_qs.aggregate(total=Sum('sales'))['total'] or Decimal('0')
                    py_gp    = prior_year_qs.aggregate(total=Sum('gross_profit'))['total'] or Decimal('0')
                    py_np    = sum(o.gross_profit.amount - o.indirect_expenses.amount for o in prior_year_qs)
                    context['yoy_summary'] = {
                        'prior_year': current_year - 1,
                        'sales_growth': _growth_pct(cy_sales, py_sales),
                        'gp_growth':    _growth_pct(cy_gp,    py_gp),
                        'np_growth':    _growth_pct(cy_np,    py_np),
                    }

            # context['sales_graph'] = sales_graph
            # context['purchase_graph'] = purchase_graph
            # context['gp_ratio_graph'] = gp_ratio_graph

            context['N'] = naira
        
            return render(request, self.template_name, context)
        
        return render(request, 'trade/no_record.html', {'message': f'No Trading and P & L Record for {current_year}'})

# Daily Model
class TradeDailyCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TradeDaily
    form_class = TradeDailyForm
    
    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Daily'
        next_date = self.get_queryset().latest('date').date + timedelta(days=1)
        if calendar.weekday(next_date.year, next_date.month, next_date.day) == calendar.SUNDAY:
            next_date += timedelta(days=1)
        context['next_date'] = next_date 
        return context
    
   
class TradeDailyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = TradeDaily
    
    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = kwargs['object']
        context['net_profit'] = obj.gross_profit-obj.indirect_expenses
        context['margin_ratio'] = round(100*(obj.gross_profit-obj.indirect_expenses)/obj.sales, 2)
        context['delivery_ratio'] = round(100*obj.direct_expenses/obj.sales, 2)
        context['admin_ratio'] = round(100*obj.indirect_expenses/obj.sales, 2)
        return context


class TradeDailyListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeDaily

    def test_func(self):
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_queryset(self):
        pl = TradeDaily.objects.last()
        year = pl.date.year
        return super().get_queryset().filter(date__year=year).order_by('-pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pl = TradeDaily.objects.last()
        year = pl.date.year
        records = list(TradeDaily.objects.filter(date__year=year).order_by('date'))
        gap_pks = set()
        for i in range(1, len(records)):
            if records[i].opening_value != records[i - 1].closing_value:
                gap_pks.add(records[i].pk)
        context['gap_pks'] = gap_pks
        return context


class TradeDailyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TradeDaily
    form_class = TradeDailyForm

    def test_func(self):
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        monthly = TradeMonthly.objects.filter(
            month=obj.date.strftime('%B'), year=obj.date.year
        ).first()
        if monthly and monthly.locked:
            messages.error(request, f'Period {monthly} is locked. Contact a superuser to unlock it.')
            return redirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Daily Update'
        return context

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            proposed = _capture_proposed_changes(form)
            if proposed:
                TradeAdjustmentRequest.objects.create(
                    model_name=self.model.__name__,
                    record_id=self.object.pk,
                    record_str=str(self.object),
                    requester=self.request.user,
                    proposed_changes=proposed,
                )
                messages.info(self.request, 'Your adjustment has been submitted for superuser approval.')
                return redirect(self.object.get_absolute_url())
            return redirect(self.object.get_absolute_url())
        changes = _capture_changes(form)
        response = super().form_valid(form)
        _log_update(self.request, self.object, changes)
        return response


class PLDailyReportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):

    queryset = TradeDaily.objects.all()
    template_name = 'trade/PL_daily_report.html'

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get(self, request, *args, **kwargs):
        context = dict()
        latest = self.queryset.latest('date').date

        end_str   = request.GET.get('end_date') or request.GET.get('date')
        start_str = request.GET.get('start_date')

        end_date   = datetime.datetime.strptime(end_str,   '%Y-%m-%d').date() if end_str   else latest
        start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else end_date - timedelta(days=15)

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        qs = TradeDaily.objects.filter(date__range=[start_date, end_date])

        context['date_range']  = f'{start_date.strftime("%d-%b-%Y")} to {end_date.strftime("%d-%b-%Y")}'
        context['start_date']  = start_date.strftime('%Y-%m-%d')
        context['end_date']    = end_date.strftime('%Y-%m-%d')
        context['quick_ranges'] = [
            ('7 days',    (latest - timedelta(days=7)).strftime('%Y-%m-%d'),  latest.strftime('%Y-%m-%d')),
            ('15 days',   (latest - timedelta(days=15)).strftime('%Y-%m-%d'), latest.strftime('%Y-%m-%d')),
            ('30 days',   (latest - timedelta(days=30)).strftime('%Y-%m-%d'), latest.strftime('%Y-%m-%d')),
            ('60 days',   (latest - timedelta(days=60)).strftime('%Y-%m-%d'), latest.strftime('%Y-%m-%d')),
            ('This month', datetime.date(latest.year, latest.month, 1).strftime('%Y-%m-%d'), latest.strftime('%Y-%m-%d')),
        ]
        
        if qs.exists():
            qs = qs.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
            qs = qs.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))
            qs = qs.annotate(net_ratio=ExpressionWrapper(100*F('net_profit')/F('gross_profit'), output_field=DecimalField(decimal_places=3)))
            qs = qs.annotate(gp_ratio=ExpressionWrapper(100*F('gross_profit')/F('sales'), output_field=DecimalField(decimal_places=3)))
            qs.order_by('date')
            
            latest_record = qs.latest('date') 

            landing_ratio = 100 * latest_record.direct_expenses/latest_record.purchase if latest_record.purchase.amount != 0 else 0
            admin_ratio = 100 * latest_record.indirect_expenses/latest_record.sales if latest_record.sales.amount != 0 else 0
            gross_profit_ratio = 100 * latest_record.gross_profit/latest_record.sales if latest_record.sales.amount != 0 else 0

            days = [str(i.day) for i in qs.values_list('date', flat=True)]

            sales        = [float(v) for v in qs.values_list('sales',        flat=True)]
            purchase     = [float(v) for v in qs.values_list('purchase',     flat=True)]
            expenses     = [float(v) for v in qs.values_list('expenses',     flat=True)]
            gross_profit = [float(v) for v in qs.values_list('gross_profit', flat=True)]
            np_plot      = [float(v) if v is not None else 0.0 for v in qs.values_list('net_ratio', flat=True)]
            gp_plot      = [float(v) if v is not None else 0.0 for v in qs.values_list('gp_ratio',  flat=True)]
            
            plt.bar(days, sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{end_date.strftime('%B')}")
            plt.ylabel(f'Sales Value')
            plt.figtext(.5, .9, f'Sales Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            sales_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['sales_graph'] = sales_graph

            plt.bar(days, purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{end_date.strftime('%B')}")
            plt.ylabel(f'Purchase Value')
            plt.figtext(.5, .9, f'Purchase Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            purchase_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['purchase_graph'] = purchase_graph
            
            plt.bar(days, expenses, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{end_date.strftime('%B')}")
            plt.ylabel('Expenses Value')
            plt.figtext(.5, .9, f'Expenses Incurred ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            expenses_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['expenses_graph'] = expenses_graph
            
            plt.bar(days, gross_profit, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{end_date.strftime('%B')}")
            plt.ylabel('Gross Profit Value')
            plt.figtext(.5, .9, f'Gross Profit ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            gross_profit_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['gross_profit_graph'] = gross_profit_graph
            
            if landing_ratio != 0 and admin_ratio != 0:
                plt.pie([landing_ratio, admin_ratio],
                        colors=['#ff1800', '#10d7ff'],
                        autopct="%1.2f%%",
                        explode=(0, 0.1),
                        shadow=True,
                        startangle=90,
                        wedgeprops={'linewidth': 2, 'edgecolor': '#b5b27b'},
                        textprops={'color':'0'},
                        )
                plt.legend([f'{landing_ratio:,.3f}', f'{admin_ratio:,.3f}'], loc='upper right')
                plt.figtext(.5, .9, 'Landing and Admin Cost Ratios', fontsize=20, ha='center')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=300)
                expenses_ratio_pie = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
                buf.close()
                plt.close() 
                context['expenses_ratio_pie'] = expenses_ratio_pie

            plt.plot(days, gp_plot, color='y')
            plt.figtext(.5, .9, 'Gross Profit Ratio', fontsize=20, ha='center')
            plt.grid()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            gp_plot = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close() 
            context['gp_plot'] = gp_plot
            

            plt.plot(days, np_plot)
            plt.figtext(.5, .9, 'Net Profit Ratio', fontsize=20, ha='center')
            plt.grid()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            np_plot = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close() 
            
            context['np_plot'] = np_plot
            
            context['total_sales'] = qs.aggregate(Sum('sales'))['sales__sum']
            context['sales_average'] = qs.aggregate(Avg('sales'))['sales__avg']

            context['total_purchase'] = qs.aggregate(Sum('purchase'))['purchase__sum']
            context['purchase_average'] = qs.aggregate(Avg('purchase'))['purchase__avg']

            context['total_expenses'] = qs.aggregate(Sum('expenses'))['expenses__sum']
            context['expenses_average'] = qs.aggregate(Avg('expenses'))['expenses__avg']

            context['total_gross'] = qs.aggregate(Sum('gross_profit'))['gross_profit__sum']
            context['gross_average'] = qs.aggregate(Avg('gross_profit'))['gross_profit__avg']

            context['gross_profit_ratio'] =  gross_profit_ratio
            context['dataset'] = latest_record
            return render(request, self.template_name, context)
        return render(request, 'trade/no_record.html', {'message': f'No Daily Record to Report from {from_date} to {to_date}'})


class BSListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = BalanceSheet
    ordering = ('-date')

    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_queryset(self):
        bs = BalanceSheet.objects.last()
        
        year = bs.date.year
        return super().get_queryset().filter(date__year=year)

    
class BSCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = BalanceSheet
    form_class = BSForm

    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create'

        if BalanceSheet.objects.exists():
            bs = BalanceSheet.objects.last()
        
            date = bs.date + datetime.timedelta(days=1)
            while date not in TradeDaily.objects.values_list('date', flat=True):
                date += datetime.timedelta(days=1)
                if date >= TradeDaily.objects.last().date:
                    if calendar.weekday(date.year, date.month, date.day) == 6:
                        date += datetime.timedelta(days=1)
                    break
            context['date'] = date
        return context


class BSDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = BalanceSheet

    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #pick the date from P&L account
        
        pk = kwargs['object'].pk
        qs = self.get_queryset().filter(pk=pk).values()[0]
        
        pl = TradeDaily.objects.filter(date=qs['date']) 
        if pl.exists():
            inventory = float(pl[0].closing_value.amount)
        else:
            inventory = 0.0

        obj = [
            {
                'profit': float(qs['profit']),
                'adjusted_profit': float(qs['adjusted_profit']),
                'equity': float(qs['capital']),
                'liability': float(qs['liability']),
                'loan_liability': float(qs['loan_liability'])
            },
            {
                'fixed_asset': float(qs['fixed_asset']),
                'current_asset': float(qs['current_asset']),
                'investment': float(qs['investment']),
                'suspense': float(qs['suspense']),
                'difference': float(qs['difference']),
                'sundry_debtor': float(qs['sundry_debtor'])
            }
        ]
        
        bs = mytools.BalanceSheet(obj)
        context['growth_ratio'] = bs.growth_ratio
        context['current_ratio'] = bs.current_ratio
        context['debt_to_equity_ratio'] = bs.debt_to_equity_ratio
        context['data'] = bs.source_of_fund
        context['quick_ratio'] = bs.acit_test_ratio(inventory, obj[1]['sundry_debtor'])
        return context


class BSUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BalanceSheet
    form_class = BSForm

    def test_func(self):
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            proposed = _capture_proposed_changes(form)
            if proposed:
                TradeAdjustmentRequest.objects.create(
                    model_name=self.model.__name__,
                    record_id=self.object.pk,
                    record_str=str(self.object),
                    requester=self.request.user,
                    proposed_changes=proposed,
                )
                messages.info(self.request, 'Your adjustment has been submitted for superuser approval.')
                return redirect(self.object.get_absolute_url())
            return redirect(self.object.get_absolute_url())
        changes = _capture_changes(form)
        response = super().form_valid(form)
        _log_update(self.request, self.object, changes)
        return response


class TradeWeekly(LoginRequiredMixin, UserPassesTestMixin, TemplateView):

    template_name = 'trade/trade_week.html'
    
    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = datetime.date.today().year

        # fetch from DB monday dates for the year 
        weeks = TradeDaily.objects.filter(date__year=year).dates('date', 'week')
        new_week = (weeks.last(), weeks.last() + datetime.timedelta(days=6))

        qs = TradeDaily.objects.filter(date__range=new_week)
        qs = qs.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))

        context['qs'] = {
            'count': qs.count(),
            'date': qs.last().date,
            'sales': qs.aggregate(Sum('sales'))['sales__sum'],
            'purchase': qs.aggregate(Sum('purchase'))['purchase__sum'],
            'net_profit': qs.aggregate(Sum('net_profit'))['net_profit__sum'],
            'direct_expenses': qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'],
            'indirect_expenses': qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'],
        }
        # From BS
        dates = sorted([weeks.last() + datetime.timedelta(days=n) for n in range(7)], reverse=True)
        
        for date in dates:
            qs = BalanceSheet.objects.filter(date=date)   
            if qs.exists():
                context['qs'].update(
                    {
                        'growth_ratio': qs.get().growth_ratio(),
                        'debt_to_equity_ratio': qs.get().debt_to_equity_ratio(),
                        'current_ratio': qs.get().current_ratio(),
                        'quick_ratio': qs.get().quick_ratio(),
                    }
                )
                break
        
        context['dates'] = dates
        
        date = TradeDaily.objects.filter(date__year=year).dates('date', 'month').reverse()[0]
        recent_month = date.month
        qs = TradeDaily.objects.filter(date__year=year).filter(date__month=recent_month)
        qs = qs.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))

        context['qsm'] = {
            'count': qs.count(),
            'sales': qs.aggregate(Sum('sales'))['sales__sum'],
            'purchase': qs.aggregate(Sum('purchase'))['purchase__sum'],
            'net_profit': qs.aggregate(Sum('net_profit'))['net_profit__sum'],
            'direct_expenses': qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum'],
            'indirect_expenses': qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum'],
        }
        
        qs = BalanceSheet.objects.latest('date')
        
        context['qsm'].update({
            'date': qs.date,
            'growth_ratio': qs.growth_ratio(),
            'debt_to_equity_ratio': qs.debt_to_equity_ratio(),
            'current_ratio': qs.current_ratio(),
            'quick_ratio': qs.quick_ratio()
        })
        return context


class AuditorView(LoginRequiredMixin, TemplateView):
    template_name = 'core/audit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Welcome to Auditor's page"

        if ProductExtension.objects.exists():
            product_date = ProductExtension.objects.latest('date').date
            product_qs = ProductExtension.objects.filter(date=product_date)
            product_qs = product_qs.annotate(cost_of_goods_sold=F('cost_price')*F('sell_out'))
            # product_qs = product_qs.filter(date=product_date)
        if TradeDaily.objects.exists():
            trade_date = TradeDaily.objects.latest('date').date
            trade_obj = TradeDaily.objects.get(date=trade_date)
        
            
        if product_date == trade_date:
            context['sales_value'] = Money(product_qs.aggregate(sales_value=Sum('cost_of_goods_sold'))['sales_value'], 'NGN')
            context['sales'] = trade_obj.sales
            context['expenses'] = trade_obj.direct_expenses + trade_obj.indirect_expenses
            context['net_profit'] = trade_obj.gross_profit - trade_obj.indirect_expenses
            context['stock_out'] = trade_obj.opening_value + trade_obj.purchase - trade_obj.closing_value
        context['product_date'] = product_date
        context['trade_date'] = trade_date
        
        return context


class BankAccountHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'trade/bank_account/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if BankBalance.objects.exists():
            latest_date = BankBalance.objects.latest('date').date
            qs = BankBalance.objects.filter(date=latest_date).filter(bank__account_group='Business')
            context['object_list'] = qs
            context['current_date'] = latest_date
            context['total_balance'] = qs.aggregate(Sum('bank_balance'))['bank_balance__sum']
            context['total_package'] = qs.aggregate(Sum('account_package_balance'))['account_package_balance__sum']
            context['bank_accounts_business'] = BankAccount.objects.filter(account_group='Business')
            context['bank_accounts_admin'] = BankAccount.objects.filter(account_group='Admin')
            context['alert_pks'] = {
                obj.pk for obj in qs if abs(obj.delta().amount) > BANK_DELTA_THRESHOLD
            }
            context['delta_threshold'] = BANK_DELTA_THRESHOLD
        else:
            context['no_object'] = True
        return context


class BankBalanceListViewAdmin(LoginRequiredMixin, ListView):
    model = BankBalance
    template_name = 'trade/bank_account/admin_account.html'

    def get_queryset(self):
        # this is the admin group
        if super().get_queryset().exists():
            latest_date = super().get_queryset().latest('date').date
            qs_admin = super().get_queryset().filter(date=latest_date).filter(bank__account_group='Admin')
            return qs_admin
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.get_queryset().exists():
            context['current_date'] = self.get_queryset().first().date
            context['total_balance'] = self.get_queryset().aggregate(Sum('bank_balance'))['bank_balance__sum']
            context['total_package'] = self.get_queryset().aggregate(Sum('account_package_balance'))['account_package_balance__sum']
        return context
    

class BankAccountDetailView(LoginRequiredMixin, DetailView):
    model = BankAccount
    template_name = 'trade/bank_account/bank_account_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bank'] = BankBalance.objects.filter(bank=kwargs['object']).order_by('-pk')[:10]
        return context


class BankAccountListView(LoginRequiredMixin, ListView):
    model = BankAccount
    template_name = 'trade/bank_account/bank_account_list.html'


class BankAccountUpdateView(LoginRequiredMixin, UpdateView):
    model = BankAccount
    template_name = 'trade/bank_account/bank_account_form.html'
    form_class = BankAccountForm


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'trade/bank_account/bank_account_form.html'


class BankBalanceCreateView(LoginRequiredMixin, CreateView):
    model = BankBalance
    form_class = BankBalanceForm
    template_name = 'trade/bank_account/bank_balance_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date = self.get_queryset().latest('date').date
        context['records'] = self.get_queryset().filter(date=date)
        return context


class BankBalanceDetailView(LoginRequiredMixin, DetailView):
    model = BankBalance
    template_name = 'trade/bank_account/bank_balance_detail.html'


class BankBalanceUpdateView(LoginRequiredMixin, UpdateView):
    model = BankBalance
    template_name = 'trade/bank_account/bank_balance_form.html'
    form_class = BankBalanceForm

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            proposed = _capture_proposed_changes(form)
            if proposed:
                TradeAdjustmentRequest.objects.create(
                    model_name=self.model.__name__,
                    record_id=self.object.pk,
                    record_str=str(self.object),
                    requester=self.request.user,
                    proposed_changes=proposed,
                )
                messages.info(self.request, 'Your adjustment has been submitted for superuser approval.')
                return redirect(self.object.get_absolute_url())
            return redirect(self.object.get_absolute_url())
        changes = _capture_changes(form)
        response = super().form_valid(form)
        _log_update(self.request, self.object, changes)
        return response


class BankBalanceListView(LoginRequiredMixin, ListView):
    model = BankBalance
    template_name = 'trade/bank_account/bank_balance_list.html'


class BankBalanceCopyView(LoginRequiredMixin, TemplateView):
    template_name = 'trade/bank_account/bank_balance_copy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = BankBalance.objects.get(pk=kwargs['pk'])
        obj.date = obj.date + datetime.timedelta(days=2 if obj.date.weekday()==calendar.SATURDAY else 1)
        context['form'] = BankBalanceCopyForm(instance=obj)
        return context


class CreditorHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'trade/creditors/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_entries = Creditor.objects.all().order_by('account', '-date')

        summaries = {}
        for obj in all_entries:
            if obj.account not in summaries:
                summaries[obj.account] = {
                    'account': obj.account,
                    'account_type': obj.account_type,
                    'cr_total': Money(0, 'NGN'),
                    'dr_total': Money(0, 'NGN'),
                    'last_entry': obj.date,
                    'entry_count': 0,
                }
            entry = summaries[obj.account]
            if obj.ledger == 'CR':
                entry['cr_total'] += obj.amount
            else:
                entry['dr_total'] += obj.amount
            if obj.date > entry['last_entry']:
                entry['last_entry'] = obj.date
            entry['entry_count'] += 1

        zero = Money(0, 'NGN')
        for entry in summaries.values():
            entry['balance'] = entry['cr_total'] - entry['dr_total']

        summaries_list = sorted(summaries.values(), key=lambda x: x['balance'].amount, reverse=True)
        context['summaries'] = summaries_list
        context['total_outstanding'] = sum(
            (s['balance'] for s in summaries_list if s['balance'] > zero), zero
        )
        context['has_records'] = bool(summaries_list)
        return context


class CreditorDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'trade/creditors/creditor_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = kwargs['account']
        qs = Creditor.objects.filter(account=account).order_by('-date')
        zero = Money(0, 'NGN')
        cr_total = sum((obj.amount for obj in qs if obj.ledger == 'CR'), zero)
        dr_total = sum((obj.amount for obj in qs if obj.ledger == 'DR'), zero)
        context['account'] = account
        context['transactions'] = qs
        context['cr_total'] = cr_total
        context['dr_total'] = dr_total
        context['balance'] = cr_total - dr_total
        return context


class CreditorUpdateView(LoginRequiredMixin, UpdateView):
    model = Creditor
    form_class = CreditorAccountForm
    template_name = 'trade/creditors/creditor_form.html'
    success_url = reverse_lazy('creditor-home')


class CreditorCreateView(LoginRequiredMixin, CreateView):
    model = Creditor
    form_class = CreditorAccountForm
    template_name = 'trade/creditors/creditor_form.html'


class FinancialsCreateView(LoginRequiredMixin, FormView):
    """To Create Balance Sheet and P & L from one form"""
    template_name = 'trade/financials_form.html'
    form_class = FinancialForm
    success_url = reverse_lazy('trade-home')

    def form_valid(self, form):
        trade_instance, balance_sheet_instance = form.save()  
        trade_instance.save()
        balance_sheet_instance.save()
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        trade = TradeDaily.objects.latest('date')
        bs = BalanceSheet.objects.latest('date')
        context['direct_income'] = trade.direct_income
        context['indirect_income'] = trade.indirect_income
        context['adjusted_profit'] = bs.adjusted_profit
        context['capital'] = bs.capital
        context['loan_liability'] = bs.loan_liability
        context['fixed_asset'] = bs.fixed_asset
        context['investment'] = bs.investment
        context['suspense'] = bs.suspense
        context['difference'] = bs.difference
        return context
    

class BankDeltaVarianceView(LoginRequiredMixin, TemplateView):
    template_name = 'trade/bank_account/bank_delta_variance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cutoff = datetime.date.today() - datetime.timedelta(days=90)
        qs = BankBalance.objects.filter(date__gte=cutoff).order_by('-date', 'bank__nickname')
        context['variance_records'] = [obj for obj in qs if abs(obj.delta().amount) > BANK_DELTA_THRESHOLD]
        context['threshold'] = BANK_DELTA_THRESHOLD
        context['cutoff'] = cutoff
        return context


class TradePeriodLockView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, pk):
        obj = get_object_or_404(TradeMonthly, pk=pk)
        obj.locked = not obj.locked
        if obj.locked:
            obj.locked_by = request.user
            obj.locked_at = datetime.datetime.now()
            action_label = 'locked'
        else:
            obj.locked_by = None
            obj.locked_at = None
            action_label = 'unlocked'
        obj.save()
        TradeAuditLog.objects.create(
            model_name='TradeMonthly',
            record_id=obj.pk,
            record_str=str(obj),
            user=request.user,
            changes={'period_lock': {'old': 'unlocked' if obj.locked else 'locked', 'new': action_label}},
        )
        messages.success(request, f'{obj} has been {action_label}.')
        return redirect('trade-list')


class TradeAuditLogListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeAuditLog
    template_name = 'trade/audit_log.html'
    paginate_by = 50

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()


class BreakEvenView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trade/break_even.html'

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lookback = max(1, min(int(self.request.GET.get('months', 3)), 24))

        # Average gross margin % from the last N completed monthly records
        recent = list(TradeMonthly.objects.order_by('-pk')[:lookback])
        gp_margins = [
            float(r.gross_profit.amount / r.sales.amount) * 100
            for r in recent if r.sales.amount > 0
        ]
        avg_margin_pct = round(sum(gp_margins) / len(gp_margins), 3) if gp_margins else None

        if avg_margin_pct is None:
            context['no_data'] = True
            return context

        # Per-month analysis for the current year
        latest = TradeMonthly.objects.last()
        current_year_qs = TradeMonthly.objects.filter(year=latest.year).order_by('pk')

        monthly_analysis = []
        for rec in current_year_qs:
            fixed = float(rec.indirect_expenses.amount)
            actual = float(rec.sales.amount)
            be = round(fixed / (avg_margin_pct / 100), 2) if avg_margin_pct else None
            gap = round(actual - be, 2) if be is not None else None
            safety = round(100 * gap / actual, 1) if (gap is not None and actual > 0) else None
            monthly_analysis.append({
                'month': rec.month,
                'fixed_costs': fixed,
                'actual_sales': actual,
                'break_even': be,
                'gap': gap,
                'safety_pct': safety,
                'above': gap >= 0 if gap is not None else None,
            })

        context['avg_margin_pct'] = avg_margin_pct
        context['lookback'] = lookback
        context['monthly_analysis'] = monthly_analysis
        context['current_year'] = latest.year
        return context


class TradeAdjustmentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeAdjustmentRequest
    template_name = 'trade/adjustment_list.html'
    paginate_by = 30

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        status = self.request.GET.get('status', TradeAdjustmentRequest.STATUS_PENDING)
        return TradeAdjustmentRequest.objects.filter(status=status)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', TradeAdjustmentRequest.STATUS_PENDING)
        context['pending_count'] = TradeAdjustmentRequest.objects.filter(
            status=TradeAdjustmentRequest.STATUS_PENDING
        ).count()
        return context


class TradeAdjustmentReviewView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, pk):
        adj = get_object_or_404(TradeAdjustmentRequest, pk=pk)
        if adj.status != TradeAdjustmentRequest.STATUS_PENDING:
            messages.warning(request, 'This request has already been reviewed.')
            return redirect('trade-adjustment-list')

        action = request.POST.get('action')
        review_note = request.POST.get('review_note', '')

        adj.reviewer = request.user
        adj.reviewed_at = datetime.datetime.now()
        adj.review_note = review_note

        if action == 'approve':
            from django.apps import apps
            model_class = apps.get_model('trade', adj.model_name)
            try:
                instance = model_class.objects.get(pk=adj.record_id)
                _apply_proposed_changes(instance, adj.proposed_changes)
                adj.status = TradeAdjustmentRequest.STATUS_APPROVED
                adj.save()
                audit_changes = {k: {'old': v['old_display'], 'new': v['new_display']}
                                 for k, v in adj.proposed_changes.items()}
                TradeAuditLog.objects.create(
                    model_name=adj.model_name,
                    record_id=adj.record_id,
                    record_str=adj.record_str,
                    user=request.user,
                    changes=audit_changes,
                )
                messages.success(request, f'Adjustment approved and applied to {adj.record_str}.')
            except Exception as e:
                messages.error(request, f'Could not apply changes: {e}')
                return redirect('trade-adjustment-list')

        elif action == 'reject':
            adj.status = TradeAdjustmentRequest.STATUS_REJECTED
            adj.save()
            TradeAuditLog.objects.create(
                model_name=adj.model_name,
                record_id=adj.record_id,
                record_str=adj.record_str,
                user=request.user,
                changes={'adjustment_rejected': {'old': 'pending', 'new': f'rejected — {review_note}'}},
            )
            messages.warning(request, f'Adjustment request for {adj.record_str} rejected.')

        return redirect('trade-adjustment-list')


class CashProjectionListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trade/cash_projection.html'

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()

        # Current bank balance as the starting point
        starting_balance = Money(0, 'NGN')
        if BankBalance.objects.exists():
            latest_date = BankBalance.objects.latest('date').date
            qs_bal = BankBalance.objects.filter(date=latest_date, bank__account_group='Business')
            total = qs_bal.aggregate(Sum('bank_balance'))['bank_balance__sum']
            if total:
                starting_balance = Money(total, 'NGN')
            context['balance_date'] = latest_date

        # All future (and today's) projections ordered by date
        items = list(CashProjection.objects.filter(expected_date__gte=today))
        past_items = list(CashProjection.objects.filter(expected_date__lt=today).order_by('-expected_date')[:10])

        # Build running balance
        running = starting_balance
        projected = []
        for item in items:
            running = running + item.signed_amount()
            projected.append({
                'item': item,
                'running_balance': running,
                'positive': running.amount >= 0,
            })

        context['starting_balance'] = starting_balance
        context['projected'] = projected
        context['past_items'] = past_items
        context['today'] = today
        return context


class CashProjectionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CashProjection
    form_class = CashProjectionForm
    template_name = 'trade/cash_projection_form.html'
    success_url = reverse_lazy('cash-projection-list')

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()


class CashProjectionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CashProjection
    form_class = CashProjectionForm
    template_name = 'trade/cash_projection_form.html'
    success_url = reverse_lazy('cash-projection-list')

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()


class CashProjectionDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'trade/cash_projection_form.html'

    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_NAME).exists()

    def post(self, request, pk):
        get_object_or_404(CashProjection, pk=pk).delete()
        return redirect('cash-projection-list')


class BankDepositView(LoginRequiredMixin, FormView):
    template_name = 'trade/bank_deposit_form.html'
    form_class = BankDepositForm
    success_url = reverse_lazy('bank-account-home')

    def get_initial(self) -> dict[str, Any]:
        self.queryset = BankBalance.objects.filter(bank__nickname='Cash')
        # 
        initial = {
            'amount': self.queryset.latest('date').bank_balance if self.queryset.exists() else Money(0.00, 'NGN')
        }
        return initial
    
    def form_valid(self, form: Any) -> HttpResponse:
        # pull out the cash and save
        cash_obj = self.queryset.latest('date')
        cash_obj.bank_balance = cash_obj.bank_balance - form.cleaned_data['amount']
        cash_obj.save()

        # Create a new bank balance
        # -- We add the deposit both to busy and bank
        latest_bank_balance_obj = BankBalance.objects.latest('date')
        BankBalance.objects.create(bank=form.cleaned_data['bank_account'],
                                   date = form.cleaned_data['date'],
                                   bank_balance = latest_bank_balance_obj.bank_balance + form.cleaned_data['amount'],
                                   account_package_balance = latest_bank_balance_obj.account_package_balance + form.cleaned_data['amount']
                                   )
        
        return super().form_valid(form)