import datetime
import calendar
from django.shortcuts import render
from django.views.generic import View, TemplateView
from django.db.models import F, Sum 
from staff.models import Employee, Payroll, EmployeeBalance
from stock.models import Product
from customer.models import CustomerProfile
from survey.models import Question
from apply.models import Applicant
from trade.models import TradeDaily, TradeMonthly
from warehouse.models import Stores, Renewal
from ozone import mytools


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home'
        return context

class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutView, self).get_context_data(**kwargs)
        context['title'] = 'About'
        return context    

class CompanyPageView(View):

    def get(self, request):
        md = Employee.active.filter(position='MD')
        gsm = Employee.active.filter(position='GSM')
        scm = Employee.active.filter(position='SCM')
        hrm = Employee.active.filter(position='HRM')
        acct = Employee.active.filter(position='Accountant')
        mrk = Employee.active.filter(position='Marketing Manager')
        lyst = Employee.active.filter(position='Analyst')


        context = {
            # 'company': company,
            'team': scm.union(hrm, acct, mrk, lyst),
            'gsm': gsm,
            'md': md 
        }
        return render(request, 'core/company.html', context)

class DashBoardView(TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workforce'] = Employee.active.count()
        context['products'] = Product.objects.count()
        context['customers'] = CustomerProfile.objects.count()
        context['number_of_kids'] = Question.objects.aggregate(Sum('number_kids'))['number_kids__sum']

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

        context['salaries'] = Payroll.objects.aggregate(Sum('net_pay'))['net_pay__sum']
        
        context['rent'] = Stores.objects.aggregate(Sum('rent_amount'))['rent_amount__sum']
        
        positive_grat = EmployeeBalance.objects.filter(value_type='Cr').aggregate(Sum('value'))['value__sum']
        negative_grat = EmployeeBalance.objects.filter(value_type='Dr').aggregate(Sum('value'))['value__sum']
        context['gratuity_value'] = positive_grat - negative_grat
        
        current_year = datetime.date.today().year
        context['last_year_rent'] = Renewal.objects.filter(date__year=current_year-1).aggregate(Sum('amount_paid'))['amount_paid__sum']
        last_four_years = [current_year, current_year-1, current_year-2, current_year-3]
    
        context['year_data'] = list((str(i), 
            TradeMonthly.objects.filter(year=i).aggregate(Sum('sales')).get('sales__sum'),
            TradeMonthly.objects.filter(year=i).aggregate(Sum('purchase')).get('purchase__sum'),
            Renewal.objects.filter(date__year=i).aggregate(Sum('store__rent_amount'))['store__rent_amount__sum'],
            Payroll.objects.filter(period__startswith=i).aggregate(Sum('net_pay'))['net_pay__sum'],
            TradeMonthly.objects.filter(year=i).aggregate(Sum('gross_profit')).get('gross_profit__sum'),
            TradeMonthly.objects.filter(year=i).aggregate(Sum('direct_expenses')).get('direct_expenses__sum'),
            TradeMonthly.objects.filter(year=i).aggregate(Sum('indirect_expenses')).get('indirect_expenses__sum'),
        ) 
        for i in last_four_years)

        # Applicants summary
        if Applicant.objects.exists():
            applicant = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year)
            applicants_this_year = [applicant.count(), applicant.filter(status=True).count(), applicant.filter(status=False).count(), applicant.filter(status=None).count()]
            applicant = Applicant.objects.filter(apply_date__year=datetime.datetime.now().year - 1)
            applicants_last_year = [applicant.count(), applicant.filter(status=True).count(), applicant.filter(status=False).count(), applicant.filter(status=None).count()]
        context['application_count'] = {
            str(datetime.datetime.now().year): applicants_this_year,
            str(datetime.datetime.now().year-1): applicants_last_year
        }

        # Employees
        if Payroll.objects.exists():
            all_periods = set(Payroll.objects.values_list('period', flat=True))
            lastest_10_periods = sorted(list(all_periods)[:10], reverse=True)
            periods = (f"{mytools.Period.full_months[i.split('-')[1]]}, {i.split('-')[0]}"  for i in lastest_10_periods)
            workforce = tuple(Payroll.objects.filter(period=period).count() for period in lastest_10_periods)
            total_payout = tuple(Payroll.objects.filter(period=period).aggregate(Sum('net_pay'))['net_pay__sum'] for period in lastest_10_periods)
            
            gross_profits = list(TradeMonthly.objects.filter(
                year=period.split('-')[0], 
                month=mytools.Period.full_months[period.split('-')[1]]
                ).aggregate(Sum('gross_profit'))['gross_profit__sum']
                for period in lastest_10_periods)
            
            gross_profits = list(0 if profit == None else profit for profit in gross_profits)  
            
            yields = tuple(round(x/y, 2) for x, y in zip(gross_profits, total_payout))
            average_pay = tuple(round(x/y, 2)for x, y in zip(total_payout, workforce))

        context['employee_dataset'] = list(data for data in zip(periods, workforce, yields, average_pay))
            
        return context

    