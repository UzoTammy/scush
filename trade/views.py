import datetime
from django.db.models.fields import FloatField
from django.db.models.query_utils import Q
from django.http.response import HttpResponseRedirect
from .forms import TradeMonthlyForm, TradeDailyForm
from django.shortcuts import redirect, render
from .models import *
from staff.models import Payroll
from django.urls.base import reverse_lazy
from django.db.models import Sum, F, Avg, ExpressionWrapper, DecimalField
import calendar
import io, base64
from matplotlib import pyplot as plt
import matplotlib
import numpy as np
from django.views.generic import (View, TemplateView, CreateView, ListView, DetailView, UpdateView)                            
from datetime import timedelta
from ozone import mytools


matplotlib.use('Agg')


class TradeHome(TemplateView): 
    template_name = 'trade/home.html'

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
        year = datetime.date.today().year

        daily_qs = TradeDaily.objects.annotate(gp_ratio=ExpressionWrapper(100*1000*F('gross_profit')/F('sales'), output_field=DecimalField()))
        daily = daily_qs.latest('date')

        monthly_qs = TradeMonthly.objects.filter(year=year).annotate(gp_ratio=ExpressionWrapper(100*1000*F('gross_profit')/F('sales'), output_field=DecimalField()))
        monthly = monthly_qs.last()

        if monthly_qs.filter(month='October').exists():
            quarter = self.quarter_group(monthly_qs, year, ['October', 'November', 'December'])
            context['quarter'] = 'Q4'
        elif monthly_qs.filter(month='July').exists():
            quarter = self.quarter_group(monthly_qs, year, ['July', 'August', 'September'])
            context['quarter'] = 'Q3'
        elif monthly_qs.filter(month='April').exists():
            quarter = self.quarter_group(monthly_qs, year, ['April', 'May', 'June'])
            context['quarter'] = 'Q2'
        else:
            quarter = self.quarter_group(monthly_qs, year, ['January', 'February', 'March'])
            context['quarter'] = 'Q1'

        context['sales'] = monthly_qs.aggregate(total=Sum('sales'))['total']
        context['purchase'] = monthly_qs.aggregate(total=Sum('purchase'))['total']
        context['direct_expenses'] = monthly_qs.aggregate(total=Sum('direct_expenses'))['total']
        context['indirect_expenses'] = monthly_qs.aggregate(total=Sum('indirect_expenses'))['total']
        context['gp_ratio'] = monthly_qs.aggregate(total=Avg('gp_ratio'))['total']

        
        # context['sales'] = sales
        context['daily'] = daily
        context['monthly'] = monthly

        context['quarter_one'] = {'sales': quarter[0], 
        'purchase': quarter[1], 
        'direct_expenses': quarter[2],
        'indirect_expenses': quarter[3], 
        'gp_ratio': quarter[4]/quarter[5]}
        return context
  
class PLDailyReportView(TemplateView):
    template_name = 'trade/PL_daily_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
  
        # today is three days ago
        today = datetime.date.today() - timedelta(days=4)

        year = today.year
        month = today.month
        qs = TradeDaily.objects.filter(date__year=year, date__month=month) 
            
        if qs.exists():
            qs = qs.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
            qs = qs.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))
            qs = qs.annotate(net_ratio=ExpressionWrapper(100*F('net_profit')/F('gross_profit'), output_field=DecimalField(decimal_places=3)))
            qs = qs.annotate(gp_ratio=ExpressionWrapper(100*F('gross_profit')/F('sales'), output_field=DecimalField(decimal_places=3)))
            
            # need to know why landing_ratio gives zero
            # qs = qs.annotate(landing_ratio=ExpressionWrapper(100 * (F('direct_expenses') / F('purchase')), output_field=DecimalField()))
            # qs = qs.annotate(admin_ratio=ExpressionWrapper(100 * (F('indirect_expenses') / F('sales')), output_field=DecimalField()))
            
            latest_record = qs.latest('date')
            landing_ratio = 100 * latest_record.direct_expenses/latest_record.purchase
            admin_ratio = 100 * latest_record.indirect_expenses/latest_record.sales
            gross_profit_ratio = 100 * latest_record.gross_profit/latest_record.sales

            days = [str(i.day) for i in qs.values_list('date', flat=True)]
            
            sales = qs.values_list('sales', flat=True)
            purchase = qs.values_list('purchase', flat=True)
            expenses = qs.values_list('expenses', flat=True)
            gross_profit = qs.values_list('gross_profit', flat=True)
            np_plot = qs.values_list('net_ratio', flat=True)
            gp_plot = qs.values_list('gp_ratio', flat=True)
            
            cut_off = 15
            days_x = days[len(days)-cut_off:]

            if len(days) > cut_off:
                sales_y = sales[len(days)-cut_off:]
                plt.bar(days_x, sales_y, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            else:
                plt.bar(days, sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel(f'Sales Value')
            plt.figtext(.5, .9, f'Sales Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            sales_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['sales_graph'] = sales_graph

            if len(days) > cut_off:
                purchase_y = purchase[len(days)-cut_off:]
                plt.bar(days_x, purchase_y, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            else:
                plt.bar(days, purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel(f'Purchase Value')
            plt.figtext(.5, .9, f'Purchase Volume ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            purchase_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['purchase_graph'] = purchase_graph
            
            if len(days) > cut_off:
                expenses_y = expenses[len(days)-cut_off:]
                plt.bar(days_x, expenses_y, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            else:
                plt.bar(days, expenses, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel('Expenses Value')
            plt.figtext(.5, .9, f'Expenses Incurred ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            expenses_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['expenses_graph'] = expenses_graph
            
            if len(days) > cut_off:
                gross_profit_y = gross_profit[len(days)-cut_off:]
                plt.bar(days_x, gross_profit_y, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            else:
                plt.bar(days, gross_profit, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            
            plt.xlabel(f"{today.strftime('%B')}")
            plt.ylabel('Gross Profit Value')
            plt.figtext(.5, .9, f'Gross Profit ({chr(8358)})', fontsize=20, ha='center')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            gross_profit_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close()
            context['gross_profit_graph'] = gross_profit_graph
            
            plt.pie([landing_ratio, admin_ratio],
                    colors=['#ff1800', '#10d7ff'],
                    autopct="%1.2f%%",
                    explode=(0, 0.1),
                    shadow=True,
                    startangle=90,
                    wedgeprops={'linewidth': 2, 'edgecolor': '#b5b27b'},
                    textprops={'color':'0'},
                    )
            plt.legend([f'{landing_ratio:,.3f}', f'{admin_ratio:,.3f}'], 
            ncol=2, bbox_to_anchor=(0.75, 1.0))
            plt.figtext(.5, .9, 'Landing and Admin Cost Ratios', fontsize=20, ha='center')
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            expenses_ratio_pie = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close() 
            context['expenses_ratio_pie'] = expenses_ratio_pie


            if len(days) > cut_off:
                gp_plot_y = gp_plot[len(days)-cut_off:]
                plt.plot(days_x, gp_plot_y, color='y')
            else:
                plt.plot(days, gp_plot, color='y')
            plt.figtext(.5, .9, 'Gross Profit Ratio', fontsize=20, ha='center')
            plt.grid()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300)
            gp_plot = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            buf.close()
            plt.close() 
            context['gp_plot'] = gp_plot
            

            if len(days) > cut_off:
                np_plot_y = np_plot[len(days)-cut_off:]
                plt.plot(days_x, np_plot_y)
            else:
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
        period_label = list(i[0:3] for i in period)
        
        def sales_bar(self):
            sales = self.monthly_trade.values_list('sales', flat=True)
            plt.bar(np.array(self.period_label), sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
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
            plt.bar(np.array(self.period_label), purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
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

    
    