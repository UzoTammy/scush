import datetime
from django.db.models.expressions import OrderBy
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
            net_profit_qs = self.monthly_trade.annotate(net_profit=(F('gross_profit') - F('expenses')))
            percent_margin_qs = self.monthly_trade.annotate(
                percent_margin=ExpressionWrapper(100*F('gross_profit') / F('sales'), 
                                                output_field=DecimalField()
                                                )
            )
            percent_sales_qs = self.monthly_trade.annotate(
                percent_sales=ExpressionWrapper(100*F('expenses') / F('sales'), 
                                                output_field=DecimalField()
                                                )
            )
            percent_gross_qs = self.monthly_trade.annotate(
                percent_gross=ExpressionWrapper(100*F('expenses') / F('gross_profit'), 
                                                output_field=DecimalField()
                                                )
            )
            percent_purchase_qs = self.monthly_trade.annotate(
                percent_purchase=ExpressionWrapper(100*F('expenses') / F('purchase'), 
                                                output_field=DecimalField()
                                                )
            )
            
            context['naira'] = chr(8358)
            context['record'] = self.monthly_trade.last().period,
            context['current_year_total'] = {
                'sales': self.monthly_trade.aggregate(total=Sum('sales'))['total'],
                'purchase': self.monthly_trade.aggregate(total=Sum('purchase'))['total'],
                'expenses': self.monthly_trade.aggregate(total=Sum('expenses'))['total'],
                'gross_profit': self.monthly_trade.aggregate(total=Sum('gross_profit'))['total'],
                'net_profit': net_profit_qs.aggregate(total=Sum('net_profit'))['total'],
                'percent_margin': percent_margin_qs.aggregate(total=Sum('percent_margin'))['total'],
                'percent_sales': percent_sales_qs.aggregate(total=Sum('percent_sales'))['total'],
                'percent_gross': percent_gross_qs.aggregate(total=Sum('percent_gross'))['total'],
                'percent_purchase': percent_purchase_qs.aggregate(total=Sum('percent_purchase'))['total'],
                }
            context['current_year_average'] = {
                'sales': self.monthly_trade.aggregate(average=Avg('sales'))['average'],
                'purchase': self.monthly_trade.aggregate(average=Avg('purchase'))['average'],
                'expenses': self.monthly_trade.aggregate(average=Avg('expenses'))['average'],
                'gross_profit': self.monthly_trade.aggregate(average=Avg('gross_profit'))['average'],
                'net_profit': net_profit_qs.aggregate(average=Avg('net_profit'))['average'],
                'percent_margin': percent_margin_qs.aggregate(average=Avg('percent_margin'))['average'],
                'percent_sales': percent_sales_qs.aggregate(average=Avg('percent_sales'))['average'],
                'percent_gross': percent_gross_qs.aggregate(average=Avg('percent_gross'))['average'],
                'percent_purchase': percent_purchase_qs.aggregate(average=Avg('percent_purchase'))['average'],
                }

            current_month = self.monthly_trade.last().period
            
            current_month_qs = self.monthly_trade.get(period=current_month)

            context['month'] = current_month
            context['year'] = self.current_year

            context['current_month'] = {
                'sales': current_month_qs.sales.amount,
                'purchase': current_month_qs.purchase.amount,
                'expenses': current_month_qs.expenses.amount,
                'gross_profit': current_month_qs.gross_profit.amount,
                'net_profit': net_profit_qs.get(period=current_month).net_profit,
                'percent_margin': percent_margin_qs.get(period=current_month).percent_margin,
                'percent_sales': percent_sales_qs.get(period=current_month).percent_sales,
                'percent_gross': percent_gross_qs.get(period=current_month).percent_gross,
                'percent_purchase': percent_purchase_qs.get(period=current_month).percent_purchase,
                }
        
        return context
    

class TradeCreate(CreateView):
    model = TradeMonthly
    success_url = reverse_lazy('trade-home')
    fields = '__all__'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add'
        if self.get_queryset().filter(id=3).exists():
            context['queryset_exist'] = True
            last_record_year = self.get_queryset().last().year
            last_record_month = self.get_queryset().last().period
            
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