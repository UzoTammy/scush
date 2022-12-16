
import datetime
import calendar
from django.core.mail import EmailMessage
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import (View, TemplateView, ListView, CreateView, DetailView, UpdateView)
from django.db.models import F, Sum, Avg 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from staff.models import Employee, Payroll, EmployeeBalance, RequestPermission
from stock.models import Product
from customer.models import Profile as CustomerProfile
from survey.models import Question
from apply.models import Applicant
from trade.models import TradeDaily, TradeMonthly, BalanceSheet
from warehouse.models import Stores, Renewal
from ozone import mytools
from .forms import JsonDatasetForm
from .models import JsonDataset
from django.conf import settings
from django.contrib.auth import authenticate, login
from mail import mailbox
from django.template import loader
from target.models import PositionKPIMonthly



def index(request):
    context = {
        'debug_mode': True if settings.DEBUG else False,
        'siter': 'https://www.scush.com.ng/home/'
    }
    return render(request, 'core/index.html', context)


def developer_login(request):
    user = authenticate(username='Uzo-02', password='Zebra.,/Ozone')
    if user is not None:
        login(request, user)
        return redirect('home')
    return redirect('index')

class PracticeView(View):
    def get(self, *args, **kwargs):
        return HttpResponse('number_of_user')
    

class ScushView(TemplateView):
    template_name = 'core/scush.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['scush'] = [
            # SN Process TitlePage App TemplateFile ViewsClass ModelsClass urlpath urlname
            ('Basic', 'Index', 'Core', 'index.html', 'TemplateView', '----', '/', 'index'),
            ('Basic', 'Templates', 'Core', 'scush.html', 'ScushView', '----', 'scush/', 'scush'),
            ('Basic', 'Home', 'Core', 'home.html', 'HomeView', '----', 'home/', 'home'),
            ('Basic', 'About', 'Core', 'about.html', 'AboutView', '----', 'about/', 'about'),
            ('Basic', 'CompanyPage', 'Core', 'company.html', 'CompanyPageView', '----', 'company/', 'company'),
            ('Basic', 'DashBoard', 'Core', 'dashboard.html', 'DashBoardView', '----', 'dashboard/', 'dashboard'),
            ('Basic', 'JsonList', 'Core', 'jasondata_list.html', 'JsonListView', 'JsonDataset', 'json/list/', 'json-list'),
            ('Basic', 'JsonDetail', 'Core', 'jasondata_detail.html', 'JsonDetailView', 'JsonDataset', 'json/<int:pk>/detail/', 'json-detail'),
            ('Basic', 'JsonCreate', 'Core', 'jasondata_form.html', 'JsonCreateView', 'JsonDataset', 'json/new/', 'json-new'),
            ('Basic', 'JsonUpdate', 'Core', 'jasondata_form.html', 'JsonUpdateView', 'JsonDataset', 'json/<int:pk>/update/', 'json-update'),
            ('Basic', 'JsonCatView', 'Core', 'resetting/json_cat_key.html', 'JsonCategoryKeyView', 'JsonDataset', 'json/<int:pk>/<str:key>/', 'json-cat-key'),
            ('Basic', 'JsonCatCreate', 'Core', 'resetting/json_new_value.html', 'JsonCategoryKeyValueCreateView', 'JsonDataset', 'json/<int:id>/<str:key>/new/', 'json-cat-key-new'),
            ('Basic', 'JsonCatUpdate', 'Core', 'resetting/json_cat_key_value.html', 'JsonCategoryKeyValueUpdateView', 'JsonDataset', 'json/<int:id>/<str:key>/<str:value>/', 'json-cat-key-value'),
    
            ('Application', 'Create', 'apply', 'applicant_form.html', 'ApplyCreateView', "Applicant", 'apply/new/', 'apply-create'),
            ('Application', 'All List', 'apply', 'applicant_list.html', 'ApplyListView', 'Applicant', 'apply/list/all/', 'apply'),
            ('Application', 'Pending List', 'apply', 'applicant_list_pending.html', 'ApplyListViewPending', 'Applicant', 'apply/list/pending/', 'apply-pending'),
            ('Application', 'Employed List', 'apply', 'applicant_list_employed.html', "ApplyListViewEmployed", 'Applicant', 'apply/list/employed/', 'apply-employed'),
            ('Application', 'Rejected List', 'apply', 'applicant_list_rejected.html', 'ApplyListViewRejected', 'Applicant', 'apply/list/rejected/', 'apply-rejected'),
            
        ]
        return context


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home'
        context['trade'] = TradeDaily.objects.all()
        
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


class DashBoardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

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

        qs = BalanceSheet.objects.filter(date__year=datetime.date.today().year).order_by('date')
        if qs.exists():
            obj = qs.latest('date')
            context['bs_ratios'] = {"growth_ratio": f"{obj.growth_ratio()}%", "quick_ratio": obj.quick_ratio()} 

            month = obj.date.month
            base_value = Decimal('0') if month == 1 else qs.filter(
                date__month=month-1).latest('date').growth_ratio()

        # picking target from database, first to pick from the month of balance sheet above
        # and if no record matching the month, the last record will be picked
        target_qs = PositionKPIMonthly.objects.filter(year=obj.date.year).filter(month=month)
        if target_qs.exists():
            target = target_qs.values()[0]
        else:
            target = PositionKPIMonthly.objects.values().last()
            month_name = datetime.date(2022, target['month'], 1).strftime('%B')
            context['target_message'] = f"Target in use is for {month_name}, {target['year']}"
    
        context['KPI'] = {
                'date_bs': obj.date,
                'growth': int(100 * (obj.growth_ratio() - base_value)),
            }
        # get previous growth
        for index,record in enumerate(qs):
            if record == obj:
                if record == qs[0]:
                    context['KPI'].update({'growth_1': 0})
                else:
                    context['KPI'].update({'growth_1': int(100 * qs[index-1].growth_ratio() - base_value)}) 

        context['color'] = {'growth': 'success' if context['KPI']['growth'] >= target['growth'] else 'dark'}
        
        qs = TradeDaily.objects.filter(date__year=datetime.date.today().year).order_by('date')
        if qs.exists():
            obj = qs.latest('date')
            context['pl_ratios'] = {"margin_ratio": f"{obj.margin_ratio()}%",
             "expense_ratio": obj.delivery_expense_ratio() + obj.admin_expense_ratio(),} 
            qs = qs.filter(date__month=month)
            sales = qs.aggregate(Sum('sales')).get('sales__sum')
            profit = qs.aggregate(Sum('gross_profit')).get('gross_profit__sum')
            direct_expenses = qs.aggregate(Sum('direct_expenses')).get('direct_expenses__sum')
            indirect_expenses = qs.aggregate(Sum('indirect_expenses')).get('indirect_expenses__sum')
            purchase = qs.aggregate(Sum('purchase')).get('purchase__sum')
            # purchase = qs.aggregate(Sum('purchase')).get('purchase__sum')

            context['KPI'].update({
                'date_pl': obj.date,
                'margin': int(100*100*(profit-indirect_expenses)/sales),
                'sales': int(sales/Decimal('1000000')),
                'delivery': int(100*100*direct_expenses/purchase) if purchase > Decimal('0') else 0,
                'admin': int(100*100*indirect_expenses/sales) if sales > Decimal('0') else 0
            }) 
            context['color'].update({
                'margin': 'success' if context['KPI']['margin'] >= target['margin'] else 'dark',
                'sales': 'success' if context['KPI']['sales'] >= target['sales'] else 'dark',
                'delivery': 'success' if context['KPI']['delivery'] <= target['delivery'] else 'dark',
                'admin': 'success' if context['KPI']['admin'] <= target['admin'] else 'dark',
                'total': 'success' if context['KPI']['delivery'] + context['KPI']['admin'] <= target['delivery'] + target['admin'] else 'dark',
            }) 
            
            # get salary and step it up by 20% 
            employee =  Employee.active.all()
            salary = employee.aggregate(Sum('basic_salary')).get('basic_salary__sum') + employee.aggregate(
                Sum('allowance')).get('allowance__sum')
            # step up by 20% to allow for incentive
            context['KPI'].update({
                'wf_productivity': int(10*(profit-indirect_expenses)/(Decimal('1.2')*salary)),
                })
            context['color'].update({
                'wf_productivity': 'success' if context['KPI']['wf_productivity'] >= target['wf_productivity'] else 'dark',
            }) 
            
            date = qs.last().date
            days = mytools.Month.number_of_working_days(date.year, date.month)
            # workforce = 
            man_hours = days * 10 * Employee.active.count()
            qs = RequestPermission.objects.filter(status=True).filter(date__year=date.year).filter(date__month=date.month)
            durations = list(obj.duration() for obj in qs)
            days = list(int(duration[:-1]) for duration in durations if duration[-1] == 'D')
            hours = list(int(duration[:-1]) for duration in durations if duration[-1] == 'H')
            hours = 10*sum(days) + sum(hours)
            context['KPI'].update({'man_hour': int(100*(1-hours/man_hours))})
            context['color'].update({'man_hour': 'success' if context['KPI']['man_hour'] >= target['man_hour'] else 'dark'})
            context['target'] = target

        context['salaries'] = Payroll.objects.filter(date_paid__year=datetime.date.today().year).aggregate(Sum('net_pay'))['net_pay__sum']
        
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
        # first row for the current data
        qs = Employee.active.all()
        number_of_employees = qs.count()
        qs = qs.annotate(salary=F('basic_salary') + F('allowance'))
        payout = qs.aggregate(Sum('salary'))['salary__sum']
        latest_date = TradeDaily.objects.latest('date').date
        year, month = latest_date.year, latest_date.month
        gross_profits = TradeDaily.objects.filter(date__year=year).filter(date__month=month).aggregate(
            Sum('gross_profit'))['gross_profit__sum']
        
        context['current_data'] = (
            latest_date, 
            number_of_employees, 
            round(float(gross_profits)/(1.1*float(payout)), 2),
            round((1.1*float(payout)/number_of_employees), 2)
            )
        
        if Payroll.objects.exists():
            all_periods = set(Payroll.objects.values_list('period', flat=True))
            lastest_10_periods = sorted(list(all_periods)[:10], reverse=True)
            periods = (f"{mytools.Period.full_months[i.split('-')[1]]}, {i.split('-')[0]}" for i in lastest_10_periods)
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

        if TradeMonthly.objects.exists():
            year = TradeMonthly.objects.last().year - 1
            try:
                payout = Payroll.objects.filter(period__startswith=str(year)).aggregate(Sum('net_pay'))['net_pay__sum']
                employees = Employee.active.filter(date_employed__year=year).count()
                gross_profit = TradeMonthly.objects.aggregate(Sum('gross_profit'))['gross_profit__sum']
                context['data'] = (str(year), employees, round(gross_profit/payout, 2), round(payout/employees, 2))
            except Exception as err:
                context['data'] = (str(year), 'RNR', 'RNR', 'RNR') 
                context['msg'] =  'RNR - Record Not Ready'                 
        return context
    

class KPIMailSend(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        # reminder: kwargs is a dictionary of strings
        target = eval(kwargs['target'])
        kpi = eval(kwargs['kpi'])
        
        # create and send mail
        email = EmailMessage(
            subject=f"KPI tracking for {kpi['date_bs'].strftime('%B, %Y')}",
            body=loader.render_to_string(
                'mail/business_KPI.html', 
                context={'KPI': kpi, 'target': target, 'title':'KPI tracking'}
                ),
            from_email='',
            to=[mailbox.get_email_group('All Management')],
        )
        email.content_subtype='html'
        email.send(fail_silently=True)
        return redirect('dashboard')


class PoliciesView(TemplateView):
    template_name = 'core/policies.html'


class JsonListView(LoginRequiredMixin, ListView):
    model = JsonDataset


class JsonDetailView(LoginRequiredMixin, DetailView):
    model = JsonDataset


class JsonCreateView(LoginRequiredMixin, CreateView):
    model = JsonDataset
    fields = '__all__'


class JsonUpdateView(LoginRequiredMixin, UpdateView):
    model = JsonDataset
    fields = '__all__'


class JsonCategoryKeyView(LoginRequiredMixin, DetailView):
    model = JsonDataset
    template_name='core/resetting/json_cat_key.html'


class JsonCategoryKeyValueCreateView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        obj = get_object_or_404(JsonDataset, pk=kwargs['id'])
        
        context = {
            'title': f"{obj}-{kwargs['key']}-Add New Value",
            'form': JsonDatasetForm(),
            'vars': {'pk': obj.pk, 'key': kwargs['key']}
        }
        
        return render(request, 'core/resetting/json_new_value.html', context)

    def post(self, request, *args, **kwargs):
        obj = get_object_or_404(JsonDataset, pk=kwargs['id'])
        dict_obj = obj.dataset
        list_obj = dict_obj[kwargs['key']]
        list_obj.append(request.POST['input_value'])

        dict_obj[kwargs['key']] = list_obj
        obj.dataset = dict_obj
        obj.save()

        return redirect('json-cat-key', kwargs['id'], kwargs['key'])


class JsonCategoryKeyValueUpdateView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        obj = get_object_or_404(JsonDataset, pk=kwargs['id'])
        
        context = {
            'title': f"{obj}-{kwargs['key']}-{kwargs['value']}",
            'form': JsonDatasetForm(), #EditJsonDatasetForm()
            'vars': {'pk': obj.pk, 'key': kwargs['key']}
        }
        return render(request, 'core/resetting/json_cat_key_value.html', context)

    def post(self, request, *args, **kwargs):
        obj = get_object_or_404(JsonDataset, pk=kwargs['id'])
        dict_obj = obj.dataset
        list_obj = dict_obj[kwargs['key']]
        I = list_obj.index(kwargs['value'])
        list_obj.remove(kwargs['value'])
        list_obj.insert(I, request.POST['input_value'])

        dict_obj[kwargs['key']] = list_obj
        obj.dataset = dict_obj
        obj.save()

        return redirect('json-cat-key', kwargs['id'], kwargs['key'])


    