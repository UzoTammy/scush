from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import datetime
from django.db.models.expressions import Func
from django.db.models.fields import FloatField
from django.db.models.query_utils import Q
from django.http.response import HttpResponse, HttpResponseRedirect
from .forms import TradeMonthlyForm, TradeDailyForm
from django.shortcuts import redirect, render
from .models import *
from staff.models import Employee, Payroll
from stock.models import Product
from customer.models import CustomerProfile
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

GROUP_NAME = 'Administrator'


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
        context['year'] = f'{year}'

        context['quarter_one'] = {'sales': quarter[0], 
        'purchase': quarter[1], 
        'direct_expenses': quarter[2],
        'indirect_expenses': quarter[3], 
        'gp_ratio': quarter[4]/quarter[5]}
        
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
        # if form.instance.sales == Money(0, 'NGN'):
        #     form.instance.sales = Money(1000, 'NGN')
        # if form.instance.purchase == Money(0, 'NGN'):
        #     form.instance.purchase = Money(1000, 'NGN')    
        return super().form_valid(form)


class TradeMonthlyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = TradeMonthly

    def test_func(self):
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False


class TradeMonthlyListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeMonthly
    ordering = '-id'
    
    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False


class TradeMonthlyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TradeMonthly
    fields = '__all__'

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        print(context)
        form.instance.year = context['last_record']['year']
        form.instance.month = context['last_record']['month']
        return super().form_valid(form)


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
        
        if monthly_trade.exists():
        
            """Adding derivatives: direct expenses, net Profit, percent margin"""
                    
            qs = monthly_trade.annotate(expenses=F('direct_expenses') + F('indirect_expenses'))
                    
            qs = qs.annotate(net_profit=(F('gross_profit') - F('indirect_expenses')))

            template = '%(function)s(%(expressions)s AS FLOAT)'

            gp = Func(F('gross_profit'), function='CAST', template=template)
            ide = Func(F('gross_profit'), function='CAST', template=template)
            sales = Func(F('sales'), function='CAST', template=template)
            
            qs = qs.annotate(gross_margin_ratio=ExpressionWrapper(100* self.df* gp/sales, output_field=FloatField()))
            
            qs = qs.annotate(sales_ratio=ExpressionWrapper(100* self.df* ide/sales, output_field=FloatField()))
            

            # qs = qs.annotate(gross_margin_ratio=ExpressionWrapper(100*self.df*F('gross_profit') / F('sales'), 
            #                                             output_field=DecimalField()
            #                                             ))
            # qs = qs.annotate(sales_ratio=ExpressionWrapper(100*self.df*F('indirect_expenses') / F('sales'), 
            #                                             output_field=DecimalField()
            #                                             ))
            qs = qs.annotate(gross_ratio=ExpressionWrapper(100*self.df*(F('indirect_expenses') + F('direct_expenses')) / F('gross_profit'), 
                                                        output_field=DecimalField()
                                                        ))
            qs = qs.annotate(purchase_ratio=ExpressionWrapper(100*self.df*F('indirect_expenses') / F('purchase'), 
                                                        output_field=DecimalField()
                                                        ))
            qs = qs.annotate(trade_ratio=ExpressionWrapper(100*self.df*F('expenses') / (F('purchase') + F('sales')), 
                                                        output_field=DecimalField()
                                                        ))
            # qs.exclude(sales=Money(0, 'NGN'))
            qs.order_by('id')
                
            period = monthly_trade.values_list('month', flat=True)
            period_label = list(i[0:3] for i in period)
            sales = monthly_trade.values_list('sales', flat=True)

            # plt.bar(np.array(period_label), sales, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            # plt.xlabel('Period')
            # plt.ylabel('Sales Value')
            # plt.figtext(.5, .9, f'Sales Volume ({chr(8358)})', fontsize=20, ha='center')
       
            # buf = io.BytesIO()
            # plt.savefig(buf, format='png', dpi=300)
            # sales_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            # buf.close()
            # plt.close()

            # purchase = monthly_trade.values_list('purchase', flat=True)
            # plt.bar(np.array(period_label), purchase, width=0.4, color=('#addba5', '#efef9c', '#addfef'))
            # plt.xlabel('Period')
            # plt.ylabel('Purchase Value')
            # plt.figtext(.5, .9, f'Purchase Volume ({chr(8358)})', fontsize=20, ha='center')
            # buf = io.BytesIO()
            # plt.savefig(buf, format='png', dpi=300)
            # purchase_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
            # buf.close()
            # plt.close()


            current_month = qs.last().month
            current_month_qs = qs.get(month=current_month)
        
            current_year_total = {
                'heading': f"Current Year Total ({naira}) as at {current_month}, {current_year}",
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
                
                'percent_margin': qs.aggregate(total=Avg('gross_margin_ratio'))['total']/self.df,
                'percent_sales': qs.aggregate(total=Avg('sales_ratio'))['total']/self.df,
                'percent_gross': qs.aggregate(total=Avg('gross_ratio'))['total']/self.df,
                'percent_purchase': qs.aggregate(total=Avg('purchase_ratio'))['total']/self.df,

                'expenses': qs.aggregate(total=Sum('expenses'))['total'],
                }
            
            if qs.count() >= 2:
                last_record_id = qs.last().id
                previous_record_id = last_record_id - 1
                previous_month_qs = qs.get(id=previous_record_id)

                # average = round(qs.aggregate(average=Avg('percent_margin'))['average'], 2)
                # previous_record_id = qs.last().id - 1
                # previous = round(qs.get(id=previous_record_id).percent_margin, 2)
                # current = round(qs.get(id=qs.last().id).percent_margin, 2)
                
                # plt.pie([average, previous, current],
                #         labels=['Cumm. Avg.', list(period)[-2], period.last()],
                #         colors=['#addba5', '#efef9c', '#addfef'],
                #         autopct="%1.2f%%",
                #         explode=(0, 0, 0.1),
                #         shadow=True,
                #         startangle=90,
                #         wedgeprops={'linewidth': 2, 'edgecolor': '#b5b27b'},
                #         textprops={'color': 'b'},
                #         )
                # plt.figtext(.5, .9, 'Gross Profit Ratio', fontsize=20, ha='center')
                # buf = io.BytesIO()
                # plt.savefig(buf, format='png', dpi=300)
                # gp_ratio_graph = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
                # buf.close()
                # plt.close()

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
                
                # previous_month['gross_margin_arrow'] = previous_month['percent_margin'] > current_year_total['percent_margin']
                # current_month['gross_margin_arrow'] = current_month['percent_margin'] > previous_month['percent_margin']

                # previous_month['sales_arrow'] = previous_month['percent_sales'] > current_year_total['percent_sales']
                # current_month['sales_arrow'] = current_month['percent_sales'] > previous_month['percent_sales']

                # previous_month['gross_arrow'] = previous_month['percent_gross'] > current_year_total['percent_gross']
                # current_month['gross_arrow'] = current_month['percent_gross'] > previous_month['percent_gross']

                # previous_month['purchase_arrow'] = previous_month['percent_purchase'] > current_year_total['percent_purchase']
                # current_month['purchase_arrow'] = current_month['percent_purchase'] > previous_month['percent_purchase']

                context['np_percent'] = round(100 * (current_month['net_profit']/previous_month['net_profit'] - 1), 3)
                # context['np_bool'] = current_month['net_profit'] > previous_month['net_profit']
                
                context['expense_value'] = current_month['expenses'] - previous_month['expenses']
                context['expense_bool'] = current_month['expenses'] > previous_month['expenses']
                
                context['lc_ratio'] = 100*(current_month['indirect_expenses']/current_month['purchase']) # landing cost ratio
                context['ac_ratio'] = 100*(current_month['direct_expenses']/current_month['sales']) # administrative cost ratio
                context['gp_ratio'] = current_month.get('percent_margin')
                
                context['recordset'] = (current_year_total,) # previous_month, current_month)
                context['dataset'] = qs.order_by('pk')

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
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Daily'
        return context

    def form_valid(self, form):
        # if form.instance.sales == Money(0, 'NGN'):
        #     form.instance.sales = Money(1, 'NGN')
        # if form.instance.purchase == Money(0, 'NGN'):
        #     form.instance.purchase = Money(1, 'NGN')
        return super().form_valid(form)

class TradeDailyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = TradeDaily
    
    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False


class TradeDailyListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = TradeDaily
    ordering = '-pk'

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False


class TradeDailyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TradeDaily
    form_class = TradeDailyForm

    def test_func(self):
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Daily Update'
        return context


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
        # today is three days ago
        if request.GET == {}:
            today = self.queryset.latest('date').date
            end_date = today.strftime('%Y-%m-%d')    
        else:
            end_date = request.GET['date']
            today = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            
        start_date = (today - timedelta(days=15)).strftime('%Y-%m-%d')
        
        qs = TradeDaily.objects.filter(date__range=[start_date, end_date]) 

        from_date = (today - timedelta(days=15)).strftime('%d-%b-%Y')
        to_date = today.strftime('%d-%b-%Y')
        context['date_range'] = f'{from_date} and {to_date}'    
        
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
            
            sales = qs.values_list('sales', flat=True)
            purchase = qs.values_list('purchase', flat=True)
            expenses = qs.values_list('expenses', flat=True)
            gross_profit = qs.values_list('gross_profit', flat=True)
            np_plot = qs.values_list('net_ratio', flat=True)
            gp_plot = qs.values_list('gp_ratio', flat=True)
            
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


class DashBoardView(TemplateView):
    template_name = 'trade/dashboard.html'

    
    def get_context_data(self, **kwargs):

        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        """let us consider the year of the last record"""
        if TradeMonthly.objects.exists():
            qs_last = TradeMonthly.objects.last()
            year = qs_last.year
            month = qs_last.month
            m = (str(index).zfill(2) for index, i in enumerate(calendar.month_name) if i == month)
            period = f'{year}-{next(m)}'
            net_pay = Payroll.objects.filter(period=period).aggregate(Sum('net_pay'))['net_pay__sum']
            qs = TradeMonthly.objects.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))
            net_profit = qs.filter(year=year, month=month).aggregate(Sum('net_profit'))['net_profit__sum']
            context['net_profit'] = net_profit
            context['net_pay'] = net_pay
            qs_daily_last = TradeDaily.objects.last()
            try:
                context['gp_ratio'] = 100*qs_daily_last.gross_profit/qs_daily_last.sales
            except:
                context['gp_ratio'] = 0
            context['sales'] = qs_daily_last.sales
            context['day'] = qs_daily_last.date
        context['workforce'] = Employee.active.count()
        context['products'] = Product.objects.count()
        context['customers'] = CustomerProfile.objects.count()
        context['salaries'] = Payroll.objects.aggregate(Sum('net_pay'))['net_pay__sum']
        from warehouse.models import Stores
        context['rent'] = Stores.objects.aggregate(Sum('rent_amount'))['rent_amount__sum']
        return render(request, self.template_name, context)