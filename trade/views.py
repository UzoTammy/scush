import calendar
import datetime
from django.contrib.auth.mixins import (LoginRequiredMixin, UserPassesTestMixin)
from django.db.models.expressions import Func
from django.db.models.fields import FloatField
from .forms import (BSForm, TradeMonthlyForm, TradeDailyForm)
from django.shortcuts import render
from .models import *
from stock.models import ProductExtension
from django.urls.base import reverse_lazy
from django.db.models import (Sum, F, Avg, ExpressionWrapper, DecimalField)
from matplotlib import pyplot as plt
from django.views.generic import (TemplateView, CreateView, ListView, DetailView, UpdateView)                            
from datetime import timedelta
from ozone import mytools
from core import utils as plotter


GROUP_NAME = 'Administrator'

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
        month = [obj.month for obj in self.get_queryset().order_by('pk')]
        sales = [obj.sales.amount for obj in self.get_queryset().order_by('pk')]
        context['chart'] = plotter.monthly_sales_revenue(month, sales)
        
        return context


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
        """if user is a member of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False
    
    def get_queryset(self):
        pl = TradeDaily.objects.last()
        year = pl.date.year
        return super().get_queryset().filter(date__year=year).order_by('-pk')


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
        """if user is a member of the group Admin then grant access to this view"""
        if self.request.user.groups.filter(name=GROUP_NAME).exists():
            return True
        return False

        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        return context


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
