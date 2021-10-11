import decimal

from .models import (Employee,
                     Payroll,
                     CreditNote,
                     DebitNote,
                     Terminate,
                     Reassign,
                     Suspend,
                     Permit,
                     SalaryChange,
                     EmployeeBalance)
from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import (View,
                                  TemplateView,
                                  ListView,
                                  DetailView,
                                  CreateView,
                                  UpdateView,
                                  )
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apply.models import Applicant
from djmoney.money import Money
from ozone import mytools
import calendar
import datetime
import itertools
from decimal import Decimal
from django.contrib import messages
from django.core.mail import send_mail, mail_admins, mail_managers
from django.core.validators import ValidationError
from .form import DebitForm, CreditForm
from django.template import loader
from django.db.models import (F,
                              Sum,
                              Avg,
                              Max,
                              Min,
                              DateField,
                              ExpressionWrapper)



class Salary:
    """
x = amount to pay
y = gross pay
a = net pay
b = deduction
c = outstanding

salary_payable is the amount to pay a staff after adding credit and removing debit
salary_less_tax is the staff's salary less tax
salary_to_pay is the amount company is willing to pay the staff
deduction is the amount company is to recover from staff in case of debit
outstanding is the amount the company is willing to reserve for the staff
"""

    @staticmethod
    def regime(salary_payable, salary_less_tax):
        if salary_payable > 2 * salary_less_tax:
            """condition 1: if what your earned is greater than twice 
            your salary pay 150% of salary"""
            deduction = Money(0, 'NGN')
            outstanding = salary_payable - 1.5 * salary_less_tax
            salary_payable = 1.5 * salary_less_tax
        elif 1.8 * salary_less_tax < salary_payable <= 2 * salary_less_tax:
            deduction = Money(0, 'NGN')
            outstanding = salary_payable - 1.4 * salary_less_tax
            salary_payable = 1.4 * salary_less_tax
        elif 1.6 * salary_less_tax < salary_payable <= 1.8 * salary_less_tax:
            deduction = Money(0, 'NGN')
            outstanding = salary_payable - 1.3 * salary_less_tax
            salary_payable = 1.3 * salary_less_tax
        elif 1.4 * salary_less_tax < salary_payable <= 1.6 * salary_less_tax:
            deduction = Money(0, 'NGN')
            outstanding = salary_payable - 1.2 * salary_less_tax
            salary_payable = 1.2 * salary_less_tax
        elif 1.2 * salary_less_tax < salary_payable <= 1.4 * salary_less_tax:
            deduction = Money(0, 'NGN')
            outstanding = salary_payable - 1.1 * salary_less_tax
            salary_payable = 1.1 * salary_less_tax
        elif salary_less_tax < salary_payable <= 1.2 * salary_less_tax:
            deduction = Money(0, 'NGN')
            outstanding = Money(0, 'NGN')
        elif 0.5 * salary_less_tax <= salary_payable <= salary_less_tax:
            """condition 3: Small that is between half gross pay and
            gross pay, get amount to pay"""
            deduction = salary_less_tax - salary_payable
            outstanding = Money(0, 'NGN')
        elif Money(0, 'NGN') <= salary_payable <= 0.5 * salary_less_tax:
            """condition 4: Too Small that is between zero and half gross
            pay, get less than your gross pay"""
            deduction = salary_payable
            outstanding = Money(0, 'NGN')
            salary_payable = salary_less_tax - salary_payable
        else:
            """condition 5: Too bad that is when amount to pay goes negative,
            cease and deduct gross salary"""
            deduction = salary_less_tax
            outstanding = salary_payable
            salary_payable = Money(0, 'NGN')
        return [salary_payable, deduction, outstanding]


class StaffScushView(TemplateView):
    template_name = 'staff/scush.html'


class StaffPoliciesView(TemplateView):
    template_name = 'staff/policies.html'


class StaffMainPageView(View):
    template_name = 'staff/home_page.html'
    messages_one = f"""Employees remain the most important asset of this company.
Their combined effort is the result of what we have today. However, for the purpose of leadership and direction,
we must provide policies and procedures to guide everyone towards expected result. We believe in their collaborative
effort, integrity, punctuality and passion as they carry out their various assigned tasks. Therefore, whatever we do,
our staff comes first and only with them can we pride ourselves in what we have achieved. As a company, we believe every
staff deserves respect from one another irrespective of position and status and also from our clients while they 
discharge their duty to them. In as much as we have groomed them to treat our customers as Kings and Queens. The 
happiness of our staff is important, that is what we expect them to transfer to our customers and their fellow staff. 
"""
    messages_two = f"""The most important parameter we measure is employee engagement. Those who are discretionary,
    committed, enthusiastic and involved. They don't work just for a paycheck or just for the next promotion, but work 
    on behalf of the organisation's goals. These workers are exceptional, productive and contented. 
    On the other, and unfortunately, their exist employees who chose not to be engaged, they are toxic, complaining 
    frequently, works against policies and procedures and kill the enthusiasm of engaged employees. Even though they are
    aware of their behaviour, they often tend to conceal it, making it difficult for the organisation to identify them.
    We cherish and count on your engagement as we continue to spend time together working as a team. 
"""

    @staticmethod
    def confirm_staff():
        staff_on_probation = list()
        """get all employees"""
        employees = Employee.active.all()
        """check the state"""
        for employee in employees:
            """if staff is on probation"""
            if employee.is_confirmed is False:
                today = datetime.date.today()
                days_worked = (today - employee.date_employed).days
                if days_worked > 90:
                    employee.is_confirmed = True
                    employee.save()
                else:
                    staff_on_probation.append({'code': employee.id,
                                               'name': employee.fullname(),
                                               'date': today + datetime.timedelta(90-days_worked)}
                                              )
        return sorted(staff_on_probation, key=lambda arg: arg['date'])

    def get(self, request):
        data, recordset = dict(), list()
        queryset = Employee.active.all()

        if queryset:
            for obj in queryset:
                countdown = mytools.DatePeriod.countdown(obj.staff.birth_date.strftime('%d-%m-%Y'), 10)
                if countdown >= 0:
                    data[obj.staff.first_name] = countdown

        if Reassign:
            qs_reassign = Reassign.objects.filter(reassign_type='A')

            for record in qs_reassign:
                start_date = record.start_date
                duration = record.duration
                today = datetime.date.today()
                due_date = start_date + datetime.timedelta(duration)
                days_left = (due_date - today).days
                if days_left >= 0:
                    reassign_data = {
                        'code': record.staff.id,
                        'staff': record.staff.fullname,
                        'start_date': start_date,
                        'due_date': due_date,
                        'days_left': days_left
                    }
                    recordset.append(reassign_data)

        context = {
            'countdown': sorted(data.items(), key=lambda x: x[1]),
            'title': 'Staff Home',
            'message_one': self.messages_one,
            'workforce': queryset.count(),
            'male': queryset.filter(staff__gender='MALE').count(),
            'female': queryset.filter(staff__gender='FEMALE').count(),
            'married': queryset.filter(staff__marital_status='MARRIED').count(),
            'single': queryset.filter(staff__marital_status='SINGLE').count(),

            'message_two': self.messages_two,

            'management': queryset.filter(is_management=True).count(),
            'non_management': queryset.exclude(is_management=True).count(),
            'terminated': Employee.objects.filter(status=False).count(),
            'probation': queryset.filter(is_confirmed=False).count(),

            'staff_on_probation': self.confirm_staff(),
            'reassign_data': recordset,
            'today': datetime.date.today(),
            'staff_category': 'terminate',
        }
        return render(request, self.template_name, context=context)


class StaffViews(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Terminate
    template_name = 'staff/staff_views.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get(self, request, *args, **kwargs):

        context = {
            'terminated_staff': self.get_queryset()
        }
        return render(request, self.template_name, context)


class PDFProfileView(View):

    def get(self, request):
        all_periods = list(i.period for i in Payroll.objects.all())
        all_periods = set(all_periods)
        choice = request.GET['radioPayroll']
        if choice == '1':
            context = {
                'title': 'first mail'
            }
        elif choice == '2':
            context = {
                'title': 'second mail'
            }
        elif choice == '3':
            context = {
                'title': 'second mail'
            }
        elif choice == '4':
            context = {
                'title': 'second mail'
            }
        elif choice == '5':
            context = {
                'title': 'second mail'
            }
        elif choice == '6':
            context = {
                'title': 'second mail'
            }
        elif choice == '7':
            context = {
                'title': 'second mail'
            }
        elif choice == '8':
            context = {
                'title': 'second mail'
            }
        elif choice == '9':
            context = {
                'title': 'second mail'
            }
        elif choice == '10':
            context = {
                'title': 'second mail'
            }
        else:
            context = {
                'title': ''
            }
        return render(request, 'mails/mailing_form.html', context)


class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Employee
    queryset = model.active.all()
    ordering = '-pk'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.queryset:
            employees = self.queryset.exclude(staff__last_name='Nwokoro')
            context['earliest_employee'] = employees.earliest('date_employed')
            context['latest_employee'] = employees.latest('date_employed')
            context['youngest_employee'] = employees.earliest('staff__birth_date')
            context['oldest_employee'] = employees.latest('staff__birth_date')
            context['highest_paid'] = employees.latest('basic_salary').basic_salary
            context['lowest_paid'] = employees.earliest('basic_salary').basic_salary
        return context


class StaffListPrivateView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    queryset = Employee.active.all()
    ordering = '-pk'
    template_name = 'staff/employee_list_private.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        """requires if data exist for query"""
        if self.queryset:
            workforce = self.get_queryset().count()
            basic_salary_payable = self.get_queryset().aggregate(bs=Sum('basic_salary'))
            allowance_payable = self.get_queryset().aggregate(al=Sum('allowance'))
            salary_payable = basic_salary_payable['bs'] + allowance_payable['al']

            month_days = mytools.Month.number_of_working_days(
                datetime.date.today().year,
                datetime.date.today().month)

            delta = datetime.datetime(2021, 1, 1, 17, 45, 0) - datetime.datetime(2021, 1, 1, 7, 45, 0)
            hours_spent_per_workday = delta.seconds / 3600

            daily_man_hours = hours_spent_per_workday * workforce
            monthly_man_hours = daily_man_hours * month_days

            context['monthly_man_hours'] = monthly_man_hours
            context['wage_rate'] = f'{chr(8358)}{float(salary_payable)/monthly_man_hours:,.2f}/Hr'
            context['salary'] = self.get_queryset().aggregate(total=Sum(F('basic_salary') + F('allowance')))
            context['tax'] = self.get_queryset().aggregate(total=Sum('tax_amount'))
            context['salary_management'] = self.get_queryset().filter(is_management=True).aggregate(total=Sum(F('basic_salary') + F('allowance')))
            context['salary_non_management'] = self.get_queryset().filter(is_management=False).aggregate(total=Sum(F('basic_salary') + F('allowance')))
            context['balance'] = self.get_queryset().aggregate(total=Sum('balance'))
        return context


class StaffListPicturesView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'staff/employee_pictures.html'
    queryset = model.active.all()
    ordering = '-pk'
    paginate_by = 4


class StaffDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def leave(self):
        """This year's man hour"""
        days_in_year = int(datetime.date(datetime.date.today().year, 12, 31).strftime('%j'))
        full_year_workdays = days_in_year - 52
        allocation = 0.04  # 4% of full_year_workdays
        return int(full_year_workdays * allocation)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.get_queryset().get(pk=kwargs['object'].pk)
        leave = (1 - person.date_employed.month / 12) * self.leave() if person.date_employed.year == datetime.date.today().year else self.leave()

        permit = Permit.objects.filter(staff_id=person)

        if permit.exists():
            permit = permit.annotate(delta=F('ending_at') - F('starting_from'))
            days_consumed = permit.aggregate(total=Sum('delta'))['total'].days
        else:
            days_consumed = 0

        balance = EmployeeBalance.objects.filter(staff_id=person)
        if balance.exists():
            credit = balance.filter(value_type='Cr')
            debit = balance.filter(value_type='Dr')
            credit_value = credit.aggregate(total=Sum('value'))['total'] if credit else Decimal('0')
            debit_value = debit.aggregate(total=Sum('value'))['total'] if debit else Decimal('0')
            total_balance = credit_value - debit_value
        else:
            total_balance = Decimal('0.00')

        context['naira'] = chr(8358)
        context['permissible_days'] = int(leave)
        context['consumed_days'] = days_consumed
        context['permit_count'] = 'None' if days_consumed == 0 else permit.count()
        context['balance_days'] = int(leave) - days_consumed
        context['positions'] = (i[0] for i in Employee.POSITIONS)
        context['branches'] = (i[0] for i in Employee.BRANCHES)

        context['reassigned'] = Reassign.objects.filter(staff_id=person)
        context['permissions'] = Permit.objects.filter(staff_id=person)
        context['suspensions'] = Suspend.objects.filter(staff_id=person)
        context['salary_changed'] = SalaryChange.objects.filter(staff_id=person)
        context['total_balance'] = total_balance
        context['payout'] = Payroll.objects.filter(staff_id=self.kwargs['pk']).aggregate(total=Sum('net_pay'))['total']
        return context


class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Employee
    fields = ('date_employed', 'is_management', 'position',
              'department', 'branch', 'banker', 'account_number',
              'basic_salary', 'allowance', 'tax_amount')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        applicant_obj = Applicant.objects.get(id=self.request.path_info.split('/')[3])
        context = super().get_context_data(**kwargs)
        context['title'] = 'New'
        context['applicant_obj'] = applicant_obj
        return context

    def form_valid(self, form):
        form.instance.staff_id = Applicant.objects.get(id=self.request.path_info.split('/')[3]).pk
        """Change applicant's status to employed"""
        applicant = Applicant.objects.get(id=form.instance.staff_id)
        applicant.status = True
        applicant.save()
        """Send mail to applicant and admin before overwriting save"""
        return super().form_valid(form)


class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee
    fields = '__all__'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

    def form_valid(self, form):
        if form.instance.image.name == '':
            form.instance.image.name = 'default.jpg'
            form.save()
        return super().form_valid(form)


class CreditNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CreditNote
    template_name = 'staff/payroll/credit_list.html'
    ordering = '-pk'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class CreditNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CreditForm
    template_name = 'staff/payroll/creditnote_form.html'
    success_url = reverse_lazy('salary')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class DebitNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = DebitNote
    template_name = 'staff/payroll/debit_list.html'
    ordering = '-pk'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class DebitNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = DebitForm
    template_name = 'staff/payroll/debitnote_form.html'
    success_url = reverse_lazy('salary')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        messages.success(request, 'Saved Successfully !!!')
        return redirect(self.get_success_url())


class StartGeneratePayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'staff/payroll/salary.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        context['months'] = mytools.Period.full_months
        context['current_month'] = str(today.month).zfill(2)
        context['years'] = (str(today.year-1), str(today.year), str(today.year+1))

        # year = today.year
        # month = today.month
        # last_month = mytools.Month.last_month()
        # next_month = mytools.Month.next_month()
        # context['last_month'] = datetime.date(year, last_month, calendar.mdays[last_month]).strftime('%B')
        # context['this_month'] = today.strftime('%B')
        # context['next_month'] = datetime.date(year, next_month, calendar.mdays[next_month]).strftime('%B')
        # context['last_period'] = f"{year}-{str(month - 1).zfill(2)}"
        # context['current_period'] = f"{year}-{str(month).zfill(2)}"
        # context['next_period'] = f"{year}-{str(month + 1).zfill(2)}"

        payroll = Payroll.objects.all()
        if payroll.exists():
            last = Payroll.objects.all().last()
            context['last_period_generated'] = last.period

            """If payroll record exist, then get the last record's period and convert to integer"""
            month_in_period = int(last.period.split('-')[1])
            year_in_period = int(last.period.split('-')[0])
            """Get the last six recent periods into a list object, starting from the period of 
            the last record in payroll"""
            periods = [last.period]
            for i in range(3):
                payroll_periods = mytools.Period(year_in_period, month_in_period - i)
                periods.append(payroll_periods.previous())
            """From the list of periods, get the name of the months"""
            recent_months = list()
            for period in periods:
                year = int(period.split('-')[0])
                month = int(period.split('-')[1])
                days = calendar.mdays[month]
                recent_months.append((year, datetime.date(year, month, days).strftime('%B')))

            all_periods_queryset = set(i.period for i in Payroll.objects.all())
            all_periods_dict = list({'year': i.split('-')[0],
                                     'month': i.split('-')[1],
                                     'month_in_words': mytools.Period.full_months[i.split('-')[1]]
                                     } for i in all_periods_queryset)
            period_by_year = itertools.groupby(all_periods_dict, lambda p: p['year'])
            years, months = list(), list()
            for key, group in period_by_year:
                years.append(key)
                for year in group:
                    months.append(year['month_in_words'])

            context['recent_months'] = recent_months
            context['payroll_current_period'] = Payroll.objects.last().period
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.GET:
            period = f"{request.GET['year']}-{request.GET['month']}"
            return redirect('generate-payroll', period=period)
        return render(request, self.template_name, context=context)


class PayrollViews(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Payroll
    template_name = 'staff/payroll/payroll_period.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def recent_months(self, period):
        """Get the last four periods"""
        year = period.split('-')[0]
        month = period.split('-')[1]

        start = int(month)
        periods = [period,
                   f'{year}-{str(start - 1).zfill(2)}',
                   f'{year}-{str(start - 2).zfill(2)}',
                   f'{year}-{str(start - 3).zfill(2)}'
                   ]
        periods = [period,
                   f'{int(year) - 1}-12',
                   f'{int(year) - 1}-11',
                   f'{int(year) - 1}-10',
                   ] if start == 1 else periods
        periods = [period,
                   f'{year}-01',
                   f'{int(year) - 1}-12',
                   f'{int(year) - 1}-11',
                   ] if start == 2 else periods
        periods = [period,
                   f'{year}-02',
                   f'{year}-01',
                   f'{int(year) - 1}-12',
                   ] if start == 3 else periods
        return list((i, mytools.Period.full_months.get(i.split('-')[1])) for i in periods)

    def get(self, request, *args, **kwargs):
        """The most recent payroll is derived from the period of the last
        record in payroll"""
        period = kwargs.get('period')
        year = period.split('-')[0]
        month = period.split('-')[1]

        this_year = datetime.date.today().year
        years = [str(this_year)]
        context = {
            'title': 'view payroll',
            'heading': {'year': year, 'month': mytools.Period.full_months.get(month)},
            'payroll': self.get_queryset().filter(period=period),
            'salary': self.get_queryset().filter(period=period).aggregate(sum=Sum('net_pay')),
            'naira': chr(8358),
            'periods_months': self.recent_months(self.get_queryset().last().period),
            'months': mytools.Period.full_months,
            'years': years,
            'summary_period': ('Month', 'Year')
        }
        return render(request, self.template_name, context=context)


class GeneratePayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Generate payroll and save to Payroll model"""
    model = Payroll
    template_name = 'staff/payroll/generated_payroll.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employees = Employee.active.all()

        data = list()
        for employee in employees:
            record = dict()

            # cr_amount is the aggregate credit amount for a staff
            # yet to be taken
            obj_credit = CreditNote.objects.filter(period=kwargs['period'])
            obj_credit = obj_credit.filter(name=employee.id)
            cr_amount = obj_credit.aggregate(total=Sum('value'))
            cr_amount['total'] = Money('0.00', 'NGN') if cr_amount['total'] is None else Money(cr_amount['total'], 'NGN')

            # dr_amount is the aggregate debit amount for a staff
            # yet to be taken
            obj_debit = DebitNote.objects.filter(period=kwargs['period'])
            obj_debit = obj_debit.filter(name=employee.id)
            dr_amount = obj_debit.aggregate(total=Sum('value'))
            dr_amount['total'] = Money('0.00', 'NGN') if dr_amount['total'] is None else Money(dr_amount['total'], 'NGN')

            # the value to use to measure what we decide
            amount_to_pay = employee.gross_pay() + cr_amount['total'] - dr_amount['total']

            # implement salary regime function to obtain net pay, deductions
            # and outstanding
            result = Salary.regime(amount_to_pay, employee.gross_pay())

            record['code'] = employee.id
            record['staff'] = employee.fullname()
            record['salary'] = employee.salary()
            record['tax'] = employee.tax_amount
            record['gross_pay'] = employee.gross_pay()

            # """Fetch the balance of the employee record and add outstanding to it"""
            payroll_balance = Payroll.objects.filter(staff=employee.id).exclude(period=kwargs['period']).aggregate(
                total=Sum('outstanding'))
            if payroll_balance['total']:
                balance = employee.balance + Money(payroll_balance['total'], 'NGN')
            else:
                balance = employee.balance

            record['balance'] = balance
            record['credit'] = cr_amount['total']
            record['debit'] = dr_amount['total']
            record['earning'] = result[0]
            record['deduction'] = result[1]
            record['outstanding'] = result[2]
            data.append(record)

        x = kwargs['period'].split('-')
        year = x[0]
        month = datetime.date(int(year), int(x[1]), 1).strftime('%B')

        context["naira"] = chr(8358)
        context["records"] = data
        context['period'] = kwargs['period']
        context['year'] = year
        context['month'] = month
        context['salary'] = sum(i['salary'] for i in data)
        context['tax'] = sum(i['tax'] for i in data)
        context['gross_pay'] = sum(i['gross_pay'] for i in data)
        context['balance'] = sum(i['balance'] for i in data)
        context['credit'] = sum(i['credit'] for i in data)
        context['debit'] = sum(i['debit'] for i in data)
        context['net_pay'] = sum(i['earning'] for i in data)
        context['deduction'] = sum(i['deduction'] for i in data)
        context['outstanding'] = sum(i['outstanding'] for i in data)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        """Go into the payroll database and fetch data for the period"""
        queryset = self.model.objects.filter(period=context['period'])

        if queryset.exists():
            context['object'] = queryset
            context['payout'] = queryset.aggregate(total=Sum('net_pay'))['total']
            context['wages'] = queryset.aggregate(total=Sum('salary'))['total']
            context['reserve'] = queryset.aggregate(total=Sum('balance'))['total']
            return render(request, 'staff/payroll/recordexists.html', context)
        return render(request, self.template_name, context)

    def post(self, request, **kwargs):
        """Get context, get period"""
        context = self.get_context_data(**kwargs)

        """Save to database or throw error if data is unclean"""
        """record context is group"""
        for row in context['records']:
            staff = Employee.active.get(pk=row['code'])
            """get the queryset"""
            data = Payroll(period=context['period'],
                           date_paid=datetime.date.today(),
                           staff=staff,
                           salary=round(row['salary'], 2),
                           tax=round(row['tax'], 2),
                           balance=round(row['balance'], 2),
                           credit_amount=round(row['credit'], 2),
                           debit_amount=round(row['debit'], 2),
                           net_pay=round(row['earning'], 2),
                           deduction=round(row['deduction'], 2),
                           outstanding=round(row['outstanding'], 2),
                           status=False,
                           )
            try:
                data.full_clean()
                data.save()  # Save Save Save
            except ValidationError as err:
                """send mail to admin"""
                return HttpResponse(f"""Generated data is not clean. 
                Check the validity of your 
                data and try again or contact your admin. {err}.""")
            else:
                """generated outstanding in Payroll to replace balances in Employee"""
                staff.balance = data.outstanding
                staff.save()
        # end of loop #

        """Send mail to managers"""
        context.update({'user': request.user})
        mail_message = loader.render_to_string('staff/payroll/payroll_mail.html', context)

        period = context['period']
        year = period.split('-')[0]
        month = int(period.split('-')[1])
        month = datetime.date(2020, month, 1).strftime('%B')

        send_mail(f"Payroll Generated for {month}, {year}",
                  message="",
                  fail_silently=False,
                  from_email='',
                  recipient_list=['uzo.nwokoro@ozonefl.com'],
                  html_message=mail_message)
        return render(request, 'staff/payroll/payroll_reports.html', context)


class RegeneratedPayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'staff/payroll/regenerated_payroll.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, **kwargs):
        f"""get the records you want to replace with payroll data
        put it in a list of dictionaries
        2. compare the lists, if they are not equal, run the dictionaries 
        and compare"""
        context = self.get_context_data(**kwargs)
        period = request.POST['period']

        """Select again all active employees"""
        employees = Employee.active.all()

        for employee in employees:
            # cr_amount is the aggregate credit amount
            obj_credit = CreditNote.objects.filter(period=period)
            obj_credit = obj_credit.filter(name=employee.id)
            cr_amount = obj_credit.aggregate(total=Sum('value'))
            cr_amount['total'] = Money(0, 'NGN') if cr_amount['total'] is None else Money(cr_amount['total'], 'NGN')

            # dr_amount is the aggregate debit amount
            obj_debit = DebitNote.objects.filter(period=period)
            obj_debit = obj_debit.filter(name=employee.id)
            dr_amount = obj_debit.aggregate(total=Sum('value'))
            dr_amount['total'] = Money(0, 'NGN') if dr_amount['total'] is None else Money(dr_amount['total'], 'NGN')

            # the value to use to measure what we decide
            amount_to_pay = employee.gross_pay() + cr_amount['total'] - dr_amount['total']

            """implement salary regime function to obtain net pay, deductions
            and outstanding"""
            data = Salary.regime(amount_to_pay, employee.gross_pay())

            staff_id = Employee.active.get(pk=employee.id)
            payroll = Payroll.objects.filter(period=period)
            """Fetch the balance of the employee record and add outstanding to it"""
            payroll_balance = Payroll.objects.filter(staff=employee.id).exclude(period=period).aggregate(
                total=Sum('outstanding'))
            payroll_balance_value = Money(0, 'NGN') if payroll_balance['total'] is None else Money(payroll_balance['total'], 'NGN')
            balance = employee.balance + payroll_balance_value

            staff, created = payroll.update_or_create(period=period,
                                                      staff=staff_id,
                                                      defaults={
                                                          'period': period,
                                                          'staff': staff_id,
                                                          'credit_amount': cr_amount['total'],
                                                          'debit_amount': dr_amount['total'],
                                                          'net_pay': data[0],
                                                          'deduction': data[1],
                                                          'outstanding': data[2],
                                                          'salary': staff_id.basic_salary + staff_id.allowance,
                                                          'tax': staff_id.tax_amount,
                                                          'status': False,
                                                          'balance': balance,
                                                      })

        context['recordset'] = Payroll.objects.filter(period=period)
        context['period'] = period
        return render(request, self.template_name, context)


class RegeneratePayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'staff/payroll/regenerate_payroll.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def fetch_period(self, period):
        month = period.split('-')[1]
        year = period.split('-')[0]
        month = datetime.date(int(year), int(month), 1).strftime('%B')
        return f"{month}, {year}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Payroll.objects.all()
        periods = {i.period for i in qs}
        periods = sorted(periods, reverse=True)[:9]

        str_periods = [self.fetch_period(i) for i in periods]
        context['periods'] = zip(str_periods, periods)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context=context)

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        the_period = self.fetch_period(request.POST['period'])
        qs = Payroll.objects.filter(period=request.POST['period'])
        context['period'] = request.POST['period']
        context['records'] = qs
        context['the_period'] = the_period
        return render(request, self.template_name, context)


class SalaryPayment(LoginRequiredMixin, UserPassesTestMixin, ListView):
    queryset = Payroll.objects.filter(status=False)
    template_name = 'staff/payroll/start_pay.html'

    def test_func(self):
        day = datetime.date.today().day
        """We will later adjust to 25<=day<5"""
        if day > 0:
            """if user is a member of of the group HRD then grant access to this view"""
            if self.request.user.groups.filter(name='HRD').exists():
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        """Go into the queryset, pick all the periods existing for unpaid staff"""
        if self.get_queryset().exists():
            periods = []
            for i in self.get_queryset():
                if i.period not in periods:
                    periods.append(i.period)
            context['periods'] = sorted(periods, reverse=True)
            period = context['periods'][0]
            context['period'] = period
            j = period.split('-')
            context['date_period'] = f"{mytools.Period.full_months[str(j[1]).zfill(2)]}, {j[0]}"
            context['object'] = self.get_queryset().filter(period=period)
        return context

    def post(self, request, **kwargs):
        context = self.get_context_data(object_list='payroll_list', **kwargs)
        period = tuple(value for value in request.POST.items())[-1][0]
        objects = self.get_queryset().filter(period=period)
        context['object'] = objects
        context['period'] = period
        j = period.split('-')
        context['date_period'] = f"{mytools.Period.full_months[str(j[1]).zfill(2)]}, {j[0]}"
        return render(request, self.template_name, context=context)


class Payslip(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Payroll
    template_name = 'staff/payroll/pay_salary.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = get_object_or_404(Employee, pk=kwargs['object'].staff_id)
        month = int(kwargs['object'].period.split('-')[1])

        balance = EmployeeBalance.objects.filter(staff=staff).filter(date__month=month).aggregate(total=Sum('value'))['total']
        balance = decimal.Decimal('0') if balance is None else balance
        context['balance'] = balance
        
        return context

    def post(self, request, pk):
        """The update of status, date paid and the alert message for successful payment"""
        staff = self.model.objects.get(pk=request.POST['pk'])
        staff.status = True
        staff.date_paid = datetime.date.today()
        staff.save()
        messages.success(request, f"{staff} paid successfully !!!")
        return HttpResponseRedirect(reverse('start-pay'))


class PayrollStatement(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Payroll
    template_name = 'staff/payroll/statement.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get(self, request, *args, **kwargs):
        context = dict()
        staff = Employee.active.get(id=kwargs['pk'])
        payslips = self.get_queryset().filter(staff=staff.id)

        context['code'] = kwargs['pk']
        context['objects'] = payslips
        context['totals'] = 'list'
        return render(request, self.template_name, context=context)


class StaffTerminate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        if request.POST['keyWord'] == 'TERMINATE':
            """Update Employee record"""
            qs = self.get_queryset().get(id=kwargs['pk'])
            qs.status = False
            qs.save()

            """Create a terminate record"""
            term = Terminate(staff=qs,
                             termination_type=request.POST['type'],
                             remark=request.POST['remark'],
                             date=request.POST['date'])
            term.save()

            """success message"""
            messages.success(request, f"{qs} with ID {str(qs.pk).zfill(3)} is terminated successfully")
            return redirect('staff-list')

        messages.info(request, "Incorrect key word, Staff yet to be terminated")
        return redirect('employee-detail', pk=kwargs['pk'])


class StaffReassign(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        position = None if request.POST['position'] == "None" else request.POST['position']
        branch = None if request.POST['branch'] == "None" else request.POST['branch']
        qs = self.get_queryset().get(id=kwargs['pk'])

        pos = {
            'Sales': ['Driver', 'Cashier', 'Store-Keeper', 'Sales-Clerk',
                      'Stock-Keeper', 'SCM', 'GSM'],
            'Marketing': ['Sales Rep', 'Marketing Manager'],
            'Accounts': ['Account-Clerk', 'Accountant'],
            'HR': ['HRM'],
            'Admin': ['Analyst', 'MD']
        }
        """Create to reassign database"""
        date = datetime.date.today() if request.POST['start_date'] == "" else request.POST['start_date']
        duration = 0 if request.POST['type'] == 'T' or request.POST['type'] == 'C' else int(request.POST['duration'])
        reassign = Reassign(staff=qs,
                            reassign_type=request.POST['type'],
                            from_position=request.POST['current_position'],
                            from_branch=request.POST['current_branch'],
                            to_position=request.POST['position'],
                            to_branch=request.POST['branch'],
                            duration=duration,
                            remark=request.POST['remark'],
                            start_date=date,
                            )
        reassign.save()

        department = None
        for key, value in pos.items():
            if position in value:
                department = key
        qs.position = position
        qs.branch = branch
        qs.department = department
        """data modified time needs to change and mail needs"""
        qs.save()

        messages.success(request, f'Position and Branch changed to {position} and {branch} respectively')
        return redirect('employee-detail', pk=kwargs['pk'])


class StaffSuspend(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        if request.POST['startDate'] > request.POST['resumptionDate']:
            messages.info(request, 'Suspension did not apply. Resumption date must be a later date.')
        elif request.POST['startDate'] == request.POST['resumptionDate']:
            messages.info(request, 'Resumption date must defer from start date')
        else:
            """calculate the cost"""
            start_date_object = datetime.datetime.strptime(request.POST['startDate'], '%Y-%m-%d')
            resumption_date_object = datetime.datetime.strptime(request.POST['resumptionDate'], '%Y-%m-%d')

            days = (resumption_date_object - start_date_object).days
            month = start_date_object.month
            days_in_month = calendar.mdays[month-1]

            person = self.get_queryset().get(id=kwargs['pk'])
            penalty_cost = person.salary() * days/days_in_month

            suspend = Suspend(
                staff=person,
                start_date=request.POST['startDate'],
                resumption_date=request.POST['resumptionDate'],
                reason=request.POST['reason'],
                penalty=penalty_cost
            )
            suspend.save()
            debit = DebitNote(
                name=person,
                period=f'{start_date_object.year}-{str(start_date_object.month).zfill(2)}',
                debit_date=start_date_object,
                remark=f"Suspension: {request.POST['reason']}",
                value=penalty_cost,
                status=False
            )
            debit.save()
            messages.success(request, "Suspension applied successfully !!!")
        return redirect('employee-detail', pk=kwargs['pk'])


class StaffPermit(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        person = self.get_queryset().get(id=kwargs['pk'])

        start_date_object = datetime.datetime.strptime(request.POST['startFrom'], '%Y-%m-%dT%H:%M')
        ending_at_object = datetime.datetime.strptime(request.POST['endingAt'], '%Y-%m-%dT%H:%M')

        permit = Permit(
            staff=person,
            starting_from=start_date_object,
            ending_at=ending_at_object,
            reason=request.POST['reason']
        )
        permit.save()

        messages.success(request, f'Permission Granted for {(ending_at_object-start_date_object).total_seconds()/3600} Man-Hours')
        return redirect('employee-detail', pk=kwargs['pk'])


class StaffSalaryChange(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        person = self.get_queryset().get(id=kwargs['pk'])
        salary = float(request.POST['salary'])

        qs = self.get_queryset().get(id=kwargs['pk'])
        previous_pay = qs.basic_salary + qs.allowance
        if qs.is_management:
            basic_salary = 0.4 * salary
            allowance = 0.6 * salary
        else:
            basic_salary = 0.6 * salary
            allowance = 0.4 * salary

        qs.basic_salary = Money(basic_salary, 'NGN')
        qs.allowance = Money(allowance, 'NGN')
        qs.save()

        change_salary = SalaryChange(staff=person,
                                     previous_value=previous_pay,
                                     value=Money(salary, 'NGN'),
                                     remark=request.POST['remark']
                                     )
        change_salary.save()
        messages.success(request, f"Salary Change is successful")
        return redirect('employee-detail', pk=kwargs['pk'])


class PayrollSummaryView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Payroll

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_dict(self, queryset):
        data = dict()
        data['number'] = queryset.count()
        data['average'] = queryset.aggregate(net_pay=Avg('net_pay'))
        data['minimum'] = queryset.aggregate(net_pay=Min('net_pay'))
        data['maximum'] = queryset.aggregate(net_pay=Max('net_pay'))
        data['balance'] = queryset.aggregate(total=Sum('balance'))
        data['salary'] = queryset.aggregate(total=Sum('salary'))
        data['tax'] = queryset.aggregate(total=Sum('tax'))
        data['credit'] = queryset.aggregate(total=Sum('credit_amount'))
        data['debit'] = queryset.aggregate(total=Sum('debit_amount'))
        data['net_pay'] = queryset.aggregate(total=Sum('net_pay'))
        data['deduction'] = queryset.aggregate(total=Sum('deduction'))
        data['outstanding'] = queryset.aggregate(total=Sum('outstanding'))
        return data

    def get(self, request, *args, **kwargs):
        """Search the database for all periods
        and use set to filter out repeated periods"""
        periods_set = set(i.period for i in self.get_queryset())
        dataset = list()
        if kwargs.get('summary_period') == 'Month':
            periods = tuple(periods_set)
            for period in sorted(periods):
                queryset = self.get_queryset().filter(period=period)
                qs_dict = self.get_dict(queryset)
                qs_dict['period'] = mytools.Period.full_months.get(period.split('-')[1])
                dataset.append(qs_dict)
        else:
            year_set = set(i.split('-')[0] for i in periods_set)
            for year in sorted(year_set):
                queryset = self.get_queryset().filter(period__startswith=year)
                qs_dict = self.get_dict(queryset)
                qs_dict['period'] = year
                dataset.append(qs_dict)

        context = {
            'title': kwargs.get('summary_period'),
            'current_period': self.get_queryset().last().period,
            'dataset': tuple(dataset)
        }
        return render(request, 'staff/payroll/payroll_summary.html', context)


class ModifyGeneratedPayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Payroll
    template_name = 'staff/payroll/payroll_modify.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        """Spool from payroll database all the periods in it. 
        1. fetch all rows, 2. get period field only 3. Since this
        field is not unique, period can have same value for different
        rows. 4. Use set to eliminate repeated values."""
        periods = set(Payroll.objects.values_list('period', flat=True))
        context['periods'] = sorted(list(periods), reverse=True)

        qs = str()
        if request.GET is not {} and 'period' in request.GET:
            period = request.GET['period']
            payroll = Payroll.objects.filter(period=period)
            modify_type = request.GET['modifyType']
            if modify_type == '1':
                qs = payroll.filter(outstanding__gt=0)
        else:
            period = context['periods'][0]
        context['the_period'] = period
        context['dataset'] = Payroll.objects.filter(period=period)
        context['payroll_with_outstanding_value'] = qs
        context['the_period_in_word'] = f"{mytools.Period.full_months[period.split('-')[1]]}, {period.split('-')[0]}"
        return render(request, self.template_name, context)


class MakeOutstandingValueZero(View):

    def get(self, request, pk):
        staff = get_object_or_404(Payroll, pk=pk)
        new_pay = staff.net_pay + staff.outstanding
        staff.outstanding = Money(0, 'NGN')
        staff.net_pay = new_pay
        staff.save()
        return redirect(reverse('payroll-modify'))


class AddStaffBalance(View):

    def post(self, request, *args, **kwargs):
        staff = get_object_or_404(Employee.active, pk=kwargs['pk'])
        """Create a record of this balance"""
        value = float(request.POST.get('balance')) if request.POST.get('balance') != '' else Money(0, 'NGN')
        balance = EmployeeBalance.objects.create(staff=staff,
                                                 value=value,
                                                 value_type=request.POST.get('CrDr'),
                                                 description=request.POST.get('comment')
                                                 )
        balance.save()
        messages.success(request, 'Profile Balance changed successfully !!!')
        return redirect(staff)
        

class PKResetView(TemplateView):
    template_name = 'staff/pk_reset.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'PK Reset'
        context['codes'] = Payroll.objects.values_list('id').order_by('id'),
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if Payroll.objects.exists():
            payroll = Payroll.objects.all()
            num = range(1, payroll.count()+1)
            status = 'OK' if list(num) == list(i.id for i in payroll) else 'NOK'

            context['rows'] = {'table': 'Payroll',
                               'status': status}
        return render(request, self.template_name, context=context)


class PKResetPayroll(View):

    def get(self, request):
        messages.success(request, 'Congrats')
        return HttpResponseRedirect(reverse('pk-reset'))


class UpdateTax(UpdateView):
    model = Employee

    def get(self, request, *args, **kwargs):

        return render(request, 'staff/payroll/tax_update.html')

    def post(self, request, *args, **kwargs):
        employees = self.get_queryset()

        for employee in employees:
            annual_pay = employee.basic_salary.amount * 12
            employee.tax_amount = mytools.Taxation.evaluate(annual_pay) / 12
            employee.save()

        context = {
            'employees': employees,
        }
        messages.success(request, 'Tax updated successfully !!!')
        return redirect(reverse('update-tax'), context)


class BalanceView(ListView):
    # template_name = 'staff/balance.html'

    def get_queryset(self):
        return EmployeeBalance.objects.filter(staff_id=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cr = self.get_queryset().filter(value_type='Cr').aggregate(total=Sum('value'))['total']
        dr = self.get_queryset().filter(value_type='Dr').aggregate(total=Sum('value'))['total']
        cr = cr if cr is not None  else Decimal('0')
        dr = dr if dr is not None else Decimal('0')
        context['total_value'] = cr - dr
        context['return'] = 'detail'
        return context


class TaxList(ListView):
    model = Employee
    
    def get_template_names(self):
        
        return ['staff/payroll/tax_list.html']

class EmployeeBalanceListView(ListView):
    model = EmployeeBalance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cr = self.get_queryset().filter(value_type='Cr').aggregate(total=Sum('value'))['total']
        dr = self.get_queryset().filter(value_type='Dr').aggregate(total=Sum('value'))['total']
        cr = cr if cr is not None  else Decimal('0')
        dr = dr if dr is not None else Decimal('0')
        context['total_value'] = cr - dr
        return context


class EmployeeBalanceDetailView(DetailView):
    model = EmployeeBalance

class EmployeeBalanceUpdateView(UpdateView):
    model = EmployeeBalance
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('employee-balance-detail', kwargs={'pk': self.kwargs['pk']})