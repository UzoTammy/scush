
import datetime
import calendar
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import (View, TemplateView, ListView, CreateView, DetailView, UpdateView)
from django.db.models import F, Sum 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from staff.models import Employee, Payroll, EmployeeBalance
from stock.models import Product
from customer.models import CustomerProfile
from survey.models import Question
from apply.models import Applicant
from trade.models import TradeDaily, TradeMonthly
from warehouse.models import Stores, Renewal
from ozone import mytools
from .forms import JsonDatasetForm
from .models import JsonDataset
from django.conf import settings

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType 

# from .forms import TestForm, MyAuthenticationForm
# from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, AuthenticationForm


# This is for practical purposes
# class PracticeView(View):
#     def get(self, request, **kwargs):
#         form = UserChangeForm()
#         context = {
#                 'form': form
#             }
#         if request.GET != {}:
#             context['content'] = request.GET
#             context['content_dic'] = eval(str(request.GET).split('<QueryDict:')[1][:-1])
#         return render(request, 'core/practice.html', context)

# class PasswordView(View):
#     def get(self, request, **kwargs):
#         form = MyAuthenticationForm()
#         return render(request, 'core/password.html', {'form': form})

# The index is at urlpatterns

def index(request):
    context = {
        'debug_mode': True if settings.DEBUG else False
    }
    return render(request, 'core/index.html', context)


def developer_login(request):
    user = authenticate(username='Uzo-02', password='Zebra.,/Ozone')
    if user is not None:
        login(request, user)
        return redirect('home')
    return redirect('index')

class PracticeView(View):
    def get(self, request, **kwargs):

        content_type = ContentType.objects.get_for_model(Employee)
        permission = Permission.objects.create(
            codename='can_employ',
            name='Can Employ',
            content_type=content_type
        )
        context = {
            # 'usera': user_a,
            # 'userg': user_g
        }
        return render(request, 'core/practice.html', context)

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


class DashBoardView(LoginRequiredMixin, TemplateView):
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

