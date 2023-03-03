
"""Summary:
This script is hosting all the views for the core app. 
The core app is for general purpose, it is hosting all the activities that are required by this site which is
not specific to any app. It is good for simple things, things required by all apps or the site as a whole.

Here are the list of all that is done here
    1. The index: This is a view for the index or landing page.
    2. The developer login: This function is only used in production, just to authenticate the developer and avoid
        login in each time he want to run the site.
    3. The Scush View: This was used to help my documentation. It will be removed.
    4. Home View: This is for the landing page for staff. It requires authenticated users to be able to use the home page.
    5. The About View: It is for the about page of the site.
    6. The Company Profile: This CBV is for the company's profile.
    7. The Dashboard: CBV whose aim is to pull summary information from all apps on one page.
    8. There are other CBVs which requires examination to ascertain their relevance and continued existence.
        (All the views below the dashboard view needs to be examined)
    
"""

# all imports
import datetime
import calendar
import csv
import json
import os
from pathlib import Path

from django.core.mail import EmailMessage
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import (TemplateView, ListView, CreateView, DetailView, UpdateView)
from django.views import View
from django.db.models import F, Sum 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from staff.models import Employee, Permit
from stock.models import Product, ProductExtension
from customer.models import CustomerCredit, Profile as CustomerProfile
from apply.models import Applicant
from trade.models import TradeDaily, TradeMonthly, BalanceSheet
from warehouse.models import Stores, Renewal
from .forms import JsonDatasetForm
from .models import JsonDataset
from django.conf import settings
from django.contrib.auth import authenticate, login
from mail import mailbox
from django.template import loader
from django.urls import reverse


def index(request):
    """
    Summary:The debug mode will define the mode we are in. If it is production, debug is True and 
            will display a link to authenticate the site. A way of allowing the developer to have direct
            access without logging in. 
    """
    context = {
        'debug_mode': True if settings.DEBUG else False,
        # 'siter': 'https://www.scush.com.ng/home/'
    }
    return render(request, 'core/index.html', context)


def developer_login(request):
    """
    The developer is logged in automatically with his credentials.
    if authenticate is successful it becomes the logged in user object and if not it is none
    """
    user = authenticate(username='Uzo-02', password='Zebra.,/Ozone')
    if user is not None:
        login(request, user)
        return redirect('home')
    return redirect('index')
    

class ScushView(TemplateView):
    """
    This is to be examined to know its relevance
    """
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
    """Summary
    The home view is mainly an html page with just a title context.
    It only requires authenticated user with no permission
    """
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home'
        # context['trade'] = TradeDaily.objects.all()
        
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        BASE_DIR = Path(__file__).resolve().parent.parent

        # json file for CSV file upload
        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        if os.path.exists(filepath):
            os.remove(filepath)
        return context


class AboutView(TemplateView):
    """
        The about page will be about the importance of processes and management and 
        what they aim to achieve to improve performance of a company.
        It will explain Stock or inventory management, Customer management, and human resource management
    """
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
    """Summary: 
        For display of important information and overview of the current state of some key features
        number of active products, active customer base, and our current workforce. 
        It also displays sales and purchase for the month, application for the year, number of stores,
        and the rent paid this year. The KPIs for the month is also displayed.
    """
    template_name = 'core/dashboard.html'
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

    def exclude_sunday(self, start_date, end_date):
        """
            Function to eliminate sundays that occured between two dates
        """
        delta = end_date - start_date
        count = 0
        for i in range(delta.days + 1):
            """start date and end date inclusive"""
            current_date = start_date + datetime.timedelta(i)
            if current_date.weekday() == calendar.SUNDAY:
                count += 1
        return delta.days - count
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Employee.objects.none() or TradeDaily.objects.none() or BalanceSheet.objects.none():
            context['empty_record'] = True
            return context
        working_hours = 10
        """Number of active products currently trading, active customers and staff strength"""
        product_count = Product.objects.filter(active=True).count()
        customer_base = CustomerProfile.objects.filter(active=True).count()
        workforce = Employee.active.count()
        
        """Year to date records"""
        qs = TradeDaily.objects.filter(date__year=datetime.date.today().year)
        sales = float(qs.aggregate(Sum('sales'))['sales__sum']) if qs.exists() else 0.0
        purchase = float(qs.aggregate(Sum('purchase'))['purchase__sum']) if qs.exists() else 0.0
        
        qs = Applicant.this_year.all()
        application = qs.count() if qs.exists() else 0

        store_count = Stores.active.count()
        qs = Stores.active.filter(status=True)
        rent_paid = float(qs.aggregate(Sum('rent_amount'))['rent_amount__sum']) if qs.exists() else 0.0
        
        # growth is the ratio of money made over the financial year to the capital invested
        obj = BalanceSheet.objects.latest('date')
        growth = int(100*100*obj.profit/obj.capital) # 
            
        # From Profit & Loss for the month
        latest_date = TradeDaily.objects.latest('date').date
        qs = TradeDaily.objects.filter(date__year=latest_date.year)
            
        if qs.exists():
            """margin ratio is the profit made against the total sales revenue for the current month
                The strategy will be to get the current month from the date of the latest record. 
                This month will be used to filter the database to obtain queryset for the month
                A net profit will be derived and its aggregate will be obtained
                Likewise, the aggregate of the sales will be obtained
                The ratio of both will give the margin ratio for the month
            """
            qs=qs.filter(date__month=latest_date.month)
            qs = qs.annotate(net_profit=F('gross_profit') - F('indirect_expenses'))
            net_profit = qs.aggregate(Sum('net_profit'))['net_profit__sum']
            monthly_sales = qs.aggregate(Sum('sales'))['sales__sum']
            margin = int(100*100*net_profit/monthly_sales)
            
            # expenses = 0
            direct_expenses = qs.aggregate(Sum('direct_expenses'))['direct_expenses__sum']
            direct_ratio = 100*direct_expenses/monthly_sales
            indirect_expenses = qs.aggregate(Sum('indirect_expenses'))['indirect_expenses__sum']
            indirect_ratio = 100*indirect_expenses/monthly_sales
            expenses = int(100*(direct_ratio + indirect_ratio))
        else:
            margin, expenses, wf_prod = 0, 0, 0
        
        # The Workforce Productivity is the ratio of the salary payable and the profit made over one month period.
            # 1. get salary payable
                # i get the period
        employees = Employee.active.all()
        employees = employees.annotate(salary=F('allowance') + F('basic_salary'))
        salary_payable = employees.aggregate(Sum('salary'))['salary__sum']
        # add 20% to the salary due to incentive we pay
        salary_payable = 1.2 * float(salary_payable)
        
        try:
            wf_prod = int(100*salary_payable/float(net_profit))
        except Exception:
            wf_prod = 0
            
        number_of_employees = employees.count()
        today = datetime.date.today()
        year, month = today.year, today.month  #the month and the year on focus
        calendar_matrix = calendar.monthcalendar(year, month)
        days = [day for week in calendar_matrix for day in week if day and week[calendar.SUNDAY] != day]
        # res = [day for week in calendar_matrix for day in week if day != 0 and day != week[6]]
        days = len(days)
        man_power_employed = number_of_employees * days * working_hours #hours per day

        """"The Permission and determination of lost man-hour 
        man-hour KPI is the ratio of lost man-hour to the man-hour available for the period.
        The lost man-hour is obtained from the permissions taken.
        Permission:
        Permissions in the database is either open(True) or closed(False) from the status field.
        From the open permissions, determine the span.
            Type 1. Same month span - start date and end date are of same month
            Type 2. Consecutive month span - end date's month is ahead of start date's month by 1
            Type 3. Non-consecutive month span - end date's month is ahead of start date's month by more than 1.
        Type 1 is the simplest and days permitted is smply end date - start date excluding work free days 
        (sundays and holidays)
        Type 2, start date's month is X and end date's month is X+1. This will divide the permission into 2
            permissions = permission1 + permission2.
            permission1 = start date to start date's month end
            permission2 = end date's month start to end date  
        Type 3, start date's month is X and end date's month is greater than X + 1.
            permissions = permission1 + permission2 + ... + permissionN
            permission1 = start date to start date's month end
            permission2 and any permission in between will be the whole month
            permissionN = end date's month start to end date   
        """
        permits = Permit.objects.filter(status=True) # Open permissions
        today = datetime.date.today()
        # permits = permits.filter(ending_at__date__gte=today)
        lost_hours = []
        
        # separate permits into the 3 types
        if permits.exists():
            for permit in permits:
                start_date = permit.starting_from
                end_date = permit.ending_at
                next_period = (start_date.year+1, 1) if start_date.month == 12 else (start_date.year, start_date.month+1)
                if start_date.date() == end_date.date():
                    # no need for split
                    hours = (permit.ending_at - permit.starting_from).total_seconds()//(60*60)
                    lost_hours.append(hours)
                elif start_date.month == end_date.month and start_date.year == end_date.year:
                    # no need for split
                    days = self.exclude_sunday(start_date.date(), end_date.date())
                    lost_hours.append(days*working_hours)
                elif next_period == (end_date.year, end_date.month):
                    # need two splits and to chose 1
                    last_day = datetime.date(
                        start_date.year, start_date.month, 
                        calendar.monthrange(start_date.year, start_date.month)[1]
                    )
                    if (today.year, today.month) == (start_date.year, start_date.month):
                        days = self.exclude_sunday(start_date.date(), last_day)
                    else:
                        days = self.exclude_sunday(last_day, end_date.date())
                    lost_hours.append(days*working_hours)
                else:
                    # need more than two splits and to chose 1
                    year, month = start_date.year, start_date.month
                    next_period = (year, month)
                    periods = []
                    while next_period != (permit.ending_at.year, permit.ending_at.month):
                        next_period = (next_period[0] + 1, 1) if next_period[1] == 12 else (next_period[0], next_period[1] + 1)
                        periods.append(next_period)
                    periods.insert(0, (year, month))
                    # chose the relevant permission period
                    for i, period in enumerate(periods):
                        if period == (today.year, today.month) and (i != 0 or i != len(periods) - 1):
                            date1 = datetime.date(period[0], period[1], 1)
                            date2 = datetime.date(period[0], period[1], calendar.monthrange(period[0], period[1])[1])
                            days = self.exclude_sunday(date1, date2)
                        elif period == (today.year, today.month) and i == 0:
                            days = self.exclude_sunday(start_date, datetime.date(
                                    start_date.year, 
                                    start_date.month,
                                    calendar.monthrange(start_date.year, start_date.month)[1]
                                    ))
                        elif period ==(today.year, today.month) and i == len(periods) - 1:
                            days = self.exclude_sunday(
                                datetime.date(end_date.year, end_date.month, 1), end_date.date()
                            )
                        else:
                            days = 0    
                    lost_hours.append(days*working_hours)
            man_hour_kpi = int(100*(1 - sum(lost_hours)/man_power_employed))   
        else:
            man_hour_kpi = 100
        
        qs = CustomerCredit.objects.all()
        credit_balance = float(qs.aggregate(Sum('current_credit'))['current_credit__sum']) if qs.exists() else 0.0
        
        context['date_of_record'] = latest_date
        context['color'] = ['success', 'info', 'warning']
        context['basics'] = [('Product Count', product_count), ('Customer Base', customer_base), ('Workforce', workforce)]
        context['trades'] = [('Sales', sales), ("Purchase", purchase), ("Credits", credit_balance),('Rent Paid', rent_paid)]
        context['points'] = [
                ('Growth', growth), 
                ('Margin', margin), 
                ('Expenses', expenses), 
                ('Man-Hour', man_hour_kpi), 
                ('WFP', wf_prod)]
        context['extras'] = [('Stores', store_count), ("Application", application)]
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


class ImportCSVView(LoginRequiredMixin, TemplateView):
    template_name = 'core/import_csv.html'  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        BASE_DIR = Path(__file__).resolve().parent.parent

        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        """
            There are two major considerations here
            1. When CSV Type has been selected (stock status or standard) 
            2. When json file exist or do not exist
            These considerations decide the process and the stage we are in
            and the documentations below details them.
        """
        if 'selectedItem' in self.request.GET:
            selected_item = self.request.GET['selectedItem']
            if selected_item == 'stock_status':
                context['status'], context['standard'] = 'checked', ''
                model_fields = ProductExtension._meta.get_fields()
                fieldset = [field.name for field in model_fields]
                # filepath = os.path.join('core', 'data.json')
                data = {'fieldset': fieldset, 'title': 'Stock Status', 'switch': 1}
                with open(filepath, 'w') as wf:
                    json.dump(data, wf, indent=2)
            else:
                """Import into a json file using the username to create the file"""
                data = {'title': 'Standard', 'switch': 1}
                with open(filepath, 'w') as wf:
                    json.dump(data, wf)
                context['status'], context['standard'] = '', 'checked'
            context['selectedItem'] = selected_item
        
        filepath = os.path.join('core', f'{self.request.user}.json')
        if os.path.exists(filepath):
            """
                The page needs to load again when CSV Type is selected.
                At this stage, the created json file will be opened just to
                access the switch so that it can keep away from stage 3.
            """
            with open(filepath, 'r') as rf:
                content = rf.read()
                data = json.loads(content)
            stage = ('Stage 2: Click Next to chose file', 50)
            if data['switch'] == 2:
                """The switch directed the process to follow this path
                    because its value was defined in the post function which
                    reversed its page using the reverse function. note: stage is defined.
                    At this stage, the json file exists and the fields of the model object,
                    the headings of the csv file has been mapped into a json object
                    has been extracted into it and brought to the page.
                """
                context['title'] = data['title']
                if 'date' in data:
                    context['date'] = data['date']
            
                context['fieldset'] = data['fieldset']
                stage = ('Stage 3: File Uploaded, Save if Satisfied? Select Type again if Not satisfied?', 75)
                if 'records' in data:
                    context['records'] = data['records']
        else:
            """The initial path of the process
                Json file is created and switch is added to control process flow.
                Stage is added to define position of the flow.

                This process occurs when json file do not exist.
                Which is the case when starting the upload process.
                Note: Json file is deleted when leaving of the page.
            """
            with open(filepath, 'w') as wf:
                data = {'switch': 0}
                json.dump(data, wf)
            stage = ('Stage 1: Select CSV file to upload', 25)
        context['switch'] = data['switch']
        context['stage'] = stage
        context['standard_message'] = (
            "Chose this if your CSV file is prepared with first row as the heading and the rest rows as the records."
            )
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            # Build paths inside the project like this: BASE_DIR / 'subdir'.
            BASE_DIR = Path(__file__).resolve().parent.parent

            filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
            with open(filepath, 'r') as rf:
                content = rf.read()
                data = json.loads(content)
            
            if 'fileName' in self.request.FILES:
                filename = self.request.FILES['fileName']
                # Read the contents of the file into memory
                csv_file = filename.read().decode('utf-8')
                # Parse the CSV data using the csv module
                reader = csv.reader(csv_file.splitlines(), delimiter=',')
                if data['title'] == 'Stock Status':
                    head_0, head_1, head_2, head_3, head_4 = next(reader), next(reader), next(reader), next(reader), next(reader)
                    records = [content for content in reader]
                
                    head_4[6], head_4[2] = head_4[2], head_4[6]
                    notes = ['Passed' if head_4[0].strip().lower() == 'product code' else 'Failed']
                    notes.append('Passed' if head_4[1].strip().lower() == 'item name' else 'Failed')
                    head_4.insert(2, '')
                    notes.append('Auto')
                    notes.append('Passed' if head_4[3].strip().lower() == 'cost price' else 'Failed')
                    head_4.insert(4, '')
                    notes.append('Auto')
                    notes.append('Passed' if head_4[5].strip().lower() == 'selling price' else 'Failed')
                    head_4[6], head_4[7] = head_4[7], head_4[6]
                    notes.append('Passed' if head_4[6].strip().lower() == 'closing balance' else 'Failed')
                    head_4[8], head_4[7] = head_4[7], head_4[8]
                    head_4.insert(7, '')
                    notes.append(head_2[0].split()[1])
                    notes.append('Passed' if head_4[8].strip().lower() == 'sellout' else 'Failed')
                    head_4.insert(9, '')
                    notes.append('Auto')
                    notes.append('Passed' if head_4[10].strip().lower() == 'sales amount' else 'Failed')
                    
                    fieldset = list((a, b, c) for a, b, c in zip(data['fieldset'], head_4, notes))
                    data['fieldset'] = fieldset
                    data['records'] = records
                    data['date'] = head_2[0]
                else:
                    data['fieldset'] = next(reader)
                    data['records'] = [content for content in reader]
                    
                data['switch'] = 2    
                with open(filepath, 'w') as wf:
                    json.dump(data, wf, indent=2)
        except Exception as err:
            messages.warning(request, f"{err} {err.with_traceback()} - **File not uploaded. Check file imported, something is not right**")
        return redirect(reverse('import-csv')) #super().get(request, **kwargs) 

class SaveCSVFile(LoginRequiredMixin, View):  
    
    def get(self, request, *args, **kwargs):
        context = {}
        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        BASE_DIR = Path(__file__).resolve().parent.parent

        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        with open(filepath, 'r') as rf:
            content = rf.read() 
            json_data = json.loads(content) # this makes it a python object
            with open(filepath, 'w') as wf:
                json_data['switch'] = 3
                json.dump(json_data, wf, indent=2) # taking a dictionary object into a json object
            
        if json_data['title'] == 'Stock Status':
            context['date'] = json_data['date']
            context['switch'] = json_data['switch']
            # date = datetime.datetime.strptime(json_data['date'], '%d-%m-%Y') 
            # if 'records' in json_data['records']:
            #     for record in json_data['records']:
            #         for item in record:
            #             obj, created = ProductExtension.objects.update_or_create(
            #                 product_id=int(item[0]),
            #                 date=date,
            #                 defaults={
            #                     'cost_price': float(item[6]),
            #                     'selling_price': float(item[3]),
            #                     'stock_value': int(item[5]),
            #                     'sell_out': int(item[2]),
            #                     'sales_amount': float(item[4]),
            #                 }
            #         )
                
        context['stage'] = ('Stage 4: congrats process is complete', 100)
        messages.success(request, "Uploaded file saved Successfully !!!")
        return render(request, 'core/import_csv.html', context=context)