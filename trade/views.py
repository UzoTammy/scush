import datetime
from django.http.response import HttpResponseRedirect
from .forms import TradeMonthlyForm, TradeDailyForm
from django.shortcuts import redirect, render
from .models import *
from staff.models import Payroll
from django.urls.base import reverse_lazy
from django.db.models import Sum, F, Avg, ExpressionWrapper, DecimalField
import calendar
import io
from ozone import mytools
import base64
from matplotlib import pyplot as plt
import matplotlib
import numpy as np
from django.views.generic import (View, TemplateView, CreateView, ListView, DetailView, UpdateView)                            


matplotlib.use('Agg')
# plt.style.use('fivethirtyeight')

# Monthly Model
class TradeHome(TemplateView):
    template_name = 'trade/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if TradeDaily.objects.exists():
            
            today = datetime.date.today()
            year = today.year
            month = today.month
            qs = TradeDaily.objects.filter(date__year=year).filter(date__month=month) 
            
            days = [str(i.day) for i in qs.values_list('date', flat=True)]
            sales = qs.values_list('sales', flat=True)
            purchase = qs.values_list('purchase', flat=True)
            
            if len(days) >= 15:
                days = days[len(days)-15:]
                sales = sales[len(days)-15:]
                purchase = purchase[len(days):]

            plt.bar(np.array(days), sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel('Sales Value')
            plt.figtext(.5, .9, f'Sales Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            sales_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            
            

            plt.bar(np.array(days), purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel('Purchase Value')
            plt.figtext(.5, .9, f'Purchase Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            purchase_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
             
            
            context['total_sales'] = qs.aggregate(Sum('sales'))['sales__sum']
            context['sales_average'] = qs.aggregate(Avg('sales'))['sales__avg']
            context['total_purchase'] = qs.aggregate(Sum('purchase'))['purchase__sum']
            context['purchase_average'] = qs.aggregate(Avg('purchase'))['purchase__avg']

            context['sales_graph'] = sales_graph
            context['purchase_graph'] = purchase_graph
        return context
    


class TradeTradingReport(TemplateView):
    df = 10_000 # decimal factor

    template_name = 'trade/trading_account.html'
    payroll = Payroll.objects.all()

    current_year = datetime.date.today().year
    monthly_trade = TradeMonthly.objects.filter(year=current_year)
    
    if monthly_trade.exists():
        
        """Adding derivatives: direct expenses, net Profit, percent margin"""
                
        qs = monthly_trade.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
                
        qs = qs.annotate(net_profit=(F('gross_profit') - F('indirect_expenses')))
                
        qs = qs.annotate(percent_margin=ExpressionWrapper(100*df*F('gross_profit') / F('sales'), 
                                                    output_field=DecimalField(decimal_places=2)
                                                    ))
        qs = qs.annotate(percent_sales=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('sales'), 
                                                    output_field=DecimalField(decimal_places=2)
                                                    ))
        qs = qs.annotate(percent_gross=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('gross_profit'), 
                                                    output_field=DecimalField(decimal_places=2)
                                                    ))
        qs = qs.annotate(percent_gross=ExpressionWrapper(100*df*(F('indirect_expenses') + F('direct_expenses')) / F('gross_profit'), 
                                                    output_field=DecimalField(decimal_places=2)
                                                    ))
        qs = qs.annotate(percent_purchase=ExpressionWrapper(100*df*F('indirect_expenses') / F('purchase'), 
                                                    output_field=DecimalField(decimal_places=2)
                                                    ))

        period = monthly_trade.values_list('month', flat=True)

        def sales_bar(self):
            sales = self.monthly_trade.values_list('sales', flat=True)
            plt.bar(np.array(self.period), sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            plt.xlabel('Period')
            plt.ylabel('Sales Value')
            plt.figtext(.5, .9, f'Sales Volume ({chr(8358)})', fontsize=20, ha='center')
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            sales_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            return sales_graph

        def purchase_bar(self):
            purchase = self.monthly_trade.values_list('purchase', flat=True)
            plt.bar(np.array(self.period), purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            plt.xlabel('Period')
            plt.ylabel('Purchase Value')
            plt.figtext(.5, .9, f'Purchase Volume ({chr(8358)})', fontsize=20, ha='center')
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            purchase_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            return purchase_graph

        def gp_ratio_pie(self):
            average = round(self.qs.aggregate(average=Avg('percent_margin'))['average'], 2)
            
            if self.qs.count() >= 2:
                previous_record_id = self.qs.last().id - 1
                previous = round(self.qs.get(id=previous_record_id).percent_margin, 2)
                current = round(self.qs.get(id=self.qs.last().id).percent_margin, 2)
                
                plt.pie([average, previous, current],
                        labels=['Cumm. Avg.', list(self.period)[-2], self.period.last()],
                        colors=['#addba5', '#efef9c', '#addfef'],
                        autopct="%1.2f%%",
                        explode=(0, 0, 0.1),
                        shadow=True,
                        startangle=90,
                        wedgeprops={'linewidth': 2, 'edgecolor': '#b5b27b'},
                        textprops={'color': 'b'},
                        )
                plt.figtext(.5, .9, 'Gross Profit Ratio', fontsize=20, ha='center')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=300)
                gp_ratio_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
                buf.close()
                plt.close()
            return gp_ratio_graph

        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        naira = chr(8358)
        current_month = self.qs.last().month

        current_month_qs = self.qs.get(month=current_month)

        current_year_total = {
            'heading': f"Current Year Total ({naira}) as at {current_month}, {self.current_year}",
            'opening_stock': self.qs.get(month='January').opening_value,
            'purchase': self.qs.aggregate(total=Sum('purchase'))['total'],
            'direct_expenses': self.qs.aggregate(total=Sum('direct_expenses'))['total'],
            'gross_profit': self.qs.aggregate(total=Sum('gross_profit'))['total'],
            
            'first_total': self.qs.get(month='January').opening_value.amount + 
            self.qs.aggregate(total=Sum('purchase'))['total'] + 
            self.qs.aggregate(total=Sum('direct_expenses'))['total'] + 
            self.qs.aggregate(total=Sum('gross_profit'))['total'],
            
            'sales': self.qs.aggregate(total=Sum('sales'))['total'],
            'direct_income': self.qs.aggregate(total=Sum('direct_income'))['total'],
            'closing_stock': self.qs.last().closing_value.amount,
            
            'second_total': self.qs.last().closing_value.amount + 
            self.qs.aggregate(total=Sum('sales'))['total'] + 
            self.qs.aggregate(total=Sum('direct_income'))['total'], 
            
            'indirect_expenses': self.qs.aggregate(total=Sum('indirect_expenses'))['total'],
            'net_profit': self.qs.aggregate(total=Sum('net_profit'))['total'],
            'indirect_income': self.qs.aggregate(total=Sum('indirect_income'))['total'],
            
            'percent_margin': self.qs.aggregate(total=Avg('percent_margin'))['total']/self.df,
            'percent_sales': self.qs.aggregate(total=Avg('percent_sales'))['total']/self.df,
            'percent_gross': self.qs.aggregate(total=Avg('percent_gross'))['total']/self.df,
            'percent_purchase': self.qs.aggregate(total=Avg('percent_purchase'))['total']/self.df,

            'expenses': self.qs.aggregate(total=Sum('expenses'))['total'],
            
            }
        
        if self.qs.count() >= 2:
            last_record_id = self.qs.last().id
            previous_record_id = last_record_id - 1
            previous_month_qs = self.qs.get(id=previous_record_id)

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
            
            'percent_margin': previous_month_qs.percent_margin/self.df,
            'percent_sales': previous_month_qs.percent_sales/self.df,
            'percent_gross': previous_month_qs.percent_gross/self.df,
            'percent_purchase': previous_month_qs.percent_purchase/self.df,

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
            
            'percent_margin': current_month_qs.percent_margin/self.df,
            'percent_sales': current_month_qs.percent_sales/self.df,
            'percent_gross': current_month_qs.percent_gross/self.df,
            'percent_purchase': current_month_qs.percent_purchase/self.df,
            
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

        context['np_percent'] = round(100 * (current_month['net_profit']/previous_month['net_profit'] - 1), 3)
        context['np_bool'] = current_month['net_profit'] > previous_month['net_profit']
        
        context['expense_value'] = current_month['expenses'] - previous_month['expenses']
        context['expense_bool'] = current_month['expenses'] > previous_month['expenses']
        
        context['lc_ratio'] = 100*(current_month['indirect_expenses']/current_month['purchase']) # landing cost ratio
        context['ac_ratio'] = 100*(current_month['direct_expenses']/current_month['sales']) # administrative cost ratio
        
        context['recordset'] = [current_year_total, previous_month, current_month]
        context['N'] = naira

        context['sales_graph'] = self.sales_bar()
        context['purchase_graph'] = self.purchase_bar()
        context['gp_ratio_graph'] = self.gp_ratio_pie()
        
        return context


class TradeMonthlyCreateView(CreateView):
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


class TradeMonthlyDetailView(DetailView):
    model = TradeMonthly


class TradeMonthlyListView(ListView):
    model = TradeMonthly
    ordering = '-id'
    

class TradeMonthlyUpdateView(UpdateView):
    model = TradeMonthly
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context


# Daily Model
class TradeDailyCreateView(CreateView):
    model = TradeDaily
    form_class = TradeDailyForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Daily'
        return context
    

class TradeDailyDetailView(DetailView):
    model = TradeDaily
    

class TradeDailyListView(ListView):
    model = TradeDaily
    ordering = '-pk'


class TradeDailyUpdateView(UpdateView):
    model = TradeDaily
    form_class = TradeDailyForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Daily Update'
        return context

    
    