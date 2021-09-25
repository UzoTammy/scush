import datetime
from .form import TradeMonthlyForm
from django.shortcuts import redirect, render
from django.views.generic import (TemplateView, 
                                    CreateView,
                                    ListView,
                                    DetailView,
                                    UpdateView,
                                )                            
from .models import *
from staff.models import Payroll
from django.urls.base import reverse, reverse_lazy
from django.db.models import Sum, F, Avg, ExpressionWrapper, DecimalField
import calendar


class TradeHome(TemplateView):
    template_name = 'trade/home.html'
    payroll = Payroll.objects.all()

    current_year = datetime.date.today().year
    monthly_trade = TradeMonthly.objects.filter(year=current_year)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.monthly_trade.exists():
            df = 10_000 # decimal factor

            """Adding derivatives: direct expenses, net Profit, percent margin"""
            
            qs = self.monthly_trade.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
            
            qs = qs.annotate(net_profit=(F('gross_profit') - F('indirect_expenses')))
            
            qs = qs.annotate(
                percent_margin=ExpressionWrapper(100*df*F('gross_profit') / F('sales'), 
                                                output_field=DecimalField(decimal_places=2)
                                                )
            )

            qs = qs.annotate(
                percent_sales=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('sales'), 
                                                output_field=DecimalField(decimal_places=2)
                                                )
            )
            qs = qs.annotate(
                percent_gross=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('gross_profit'), 
                                                output_field=DecimalField(decimal_places=2)
                                                )
            )
            qs = qs.annotate(
                percent_gross=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('gross_profit'), 
                                                output_field=DecimalField(decimal_places=2)
                                                )
            )
            qs = qs.annotate(
                percent_purchase=ExpressionWrapper(100*df*F('indirect_expenses') / F('purchase'), 
                                                output_field=DecimalField(decimal_places=2)
                                                )
            )
            
            naira = chr(8358)
            current_month = qs.last().month

            current_month_qs = qs.get(month=current_month)

            current_year_total = {
                'heading': f"Current Year Total ({naira}) as at {current_month}, {self.current_year}",
                'opening_stock': qs.get(month='January').opening_value,
                'purchase': qs.aggregate(total=Sum('purchase'))['total'],
                'direct_expenses': qs.aggregate(total=Sum('direct_expenses'))['total'],
                'gross_profit': qs.aggregate(total=Sum('gross_profit'))['total'],
                
                'first_total': qs.get(month='January').opening_value.amount + 
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
                
                'percent_margin': qs.aggregate(total=Avg('percent_margin'))['total']/df,
                'percent_sales': qs.aggregate(total=Avg('percent_sales'))['total']/df,
                'percent_gross': qs.aggregate(total=Avg('percent_gross'))['total']/df,
                'percent_purchase': qs.aggregate(total=Avg('percent_purchase'))['total']/df,

                'expenses': qs.aggregate(total=Sum('expenses'))['total'],
                
                }
            
            if qs.count() >= 2:
                last_record_id = qs.last().id
                previous_record_id = last_record_id - 1
                previous_month_qs = qs.get(id=previous_record_id)

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
                
                'percent_margin': previous_month_qs.percent_margin/df,
                'percent_sales': previous_month_qs.percent_sales/df,
                'percent_gross': previous_month_qs.percent_gross/df,
                'percent_purchase': previous_month_qs.percent_purchase/df,

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
                
                'percent_margin': current_month_qs.percent_margin/df,
                'percent_sales': current_month_qs.percent_sales/df,
                'percent_gross': current_month_qs.percent_gross/df,
                'percent_purchase': current_month_qs.percent_purchase/df,
                
                'expenses': current_month_qs.expenses,
                
                }
            
            previous_month['gross_margin_arrow'] = previous_month['percent_margin'] > current_year_total['percent_margin']
            current_month['gross_margin_arrow'] = current_month['percent_margin'] > previous_month['percent_margin']

            previous_month['sales_arrow'] = previous_month['percent_sales'] > current_year_total['percent_sales']
            current_month['sales_arrow'] = current_month['percent_sales'] > previous_month['percent_sales']

            previous_month['gross_arrow'] = previous_month['percent_gross'] > current_year_total['percent_gross']
            current_month['gross_arrow'] = current_month['percent_gross'] > previous_month['percent_gross']

            previous_month['purchase_arrow'] = previous_month['percent_purchase'] > current_year_total['percent_purchase']
            current_month['purchase_arrow'] = current_month['percent_purchase'] > previous_month['percent_purchase']

            context['recordset'] = [current_year_total, previous_month, current_month]

        return context
    

class TradeCreate(CreateView):
    model = TradeMonthly
    form_class = TradeMonthlyForm
    success_url = reverse_lazy('trade-home')
    
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


class TradeDetail(DetailView):
    model = TradeMonthly


class TradeList(ListView):
    model = TradeMonthly
    ordering = '-id'
    

class TradeUpdate(UpdateView):
    model = TradeMonthly
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context