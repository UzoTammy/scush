from .models import (Employee,
                     Payroll,
                     CreditNote,
                     DebitNote,
                     Terminate,
                     Reassign,
                     Suspend,
                     Permit)
from django.shortcuts import render, reverse, redirect
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
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.admin import Group
from django.core.mail import send_mail, mail_admins, mail_managers
from django.core.validators import ValidationError
from .form import DebitForm, CreditForm
from django.template import loader
from django.db.models import F, Sum


class Salary:
    """
x = amount to pay
y = gross pay
a = net pay
b = deduction
c = outstanding"""

    @staticmethod
    def regime(x, y):
        if x > 2 * y:
            """condition 1: Too large that is greater or equals twice
             gross pay, get more than your salary"""
            b = Money(0, 'NGN')
            c = x - 1.5 * y
            x = 1.5 * y
        elif y < x <= 2 * y:
            """condition 2: Large that is between gross pay and twice
            gross pay, get full salary"""
            b = Money(0, 'NGN')
            c = x - y
            x = y
        elif 0.5 * y <= x <= y:
            """condition 3: Small that is between half gross pay and
            gross pay, get amount to pay"""
            b = y - x
            c = Money(0, 'NGN')
        elif Money(0, 'NGN') <= x <= 0.5 * y:
            """condition 4: Too Small that is between zero and half gross
            pay, get less than your gross pay"""
            b = x
            c = Money(0, 'NGN')
            x = y - x
        else:
            """condition 5: Too bad that is when amount to pay goes negative,
            cease and deduct gross salary"""
            b = y
            c = x
            x = Money(0, 'NGN')
        return x, b, c


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

    def confirm_staff(self):
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
        return staff_on_probation

    def get(self, request):
        data = dict()
        queryset = Employee.active.all()
        if queryset:
            for obj in queryset:
                countdown = mytools.DatePeriod.countdown(obj.staff.birth_date.strftime('%d-%m-%Y'), 10)
                if countdown >= 0:
                    data[obj.staff.first_name] = countdown

        context = {
            'title': 'Staff Home',
            'header': 'Staff Home Page',
            'message_one': self.messages_one,
            'workforce': queryset.count(),
            'male': queryset.filter(staff__gender='MALE').count(),
            'female': queryset.filter(staff__gender='FEMALE').count(),
            'married': queryset.filter(staff__marital_status='MARRIED').count(),
            'single': queryset.filter(staff__marital_status='SINGLE').count(),
            'countdown': sorted(data.items(), key=lambda x: x[-1]),
            'message_two': self.messages_two,
            'management': queryset.filter(is_management=True).count(),
            'non_management': queryset.exclude(is_management=True).count(),
            'terminated': Employee.objects.filter(status=False).count(),
            'probation': queryset.filter(is_confirmed=False).count(),
            'staff_on_probation': self.confirm_staff(),
            'today': datetime.date.today()
        }
        return render(request, self.template_name, context=context)


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
    model = Employee
    ordering = '-pk'
    queryset = model.active.all()
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
            results = permit.annotate(delta=F('ending_at') - F('starting_from'))
            total_days = sum(result.delta.days for result in results)
            days_consumed = int(total_days)
        else:
            days_consumed = 0
        context['permissible_days'] = int(leave)
        context['consumed_days'] = days_consumed
        context['permit_count'] = 'None' if days_consumed == 0 else permit.count()
        context['balance_days'] = int(leave) - days_consumed
        context['positions'] = (i[0] for i in Employee.POSITIONS)
        context['branches'] = (i[0] for i in Employee.BRANCHES)
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

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class CreditNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CreditForm
    template_name = 'staff/payroll/creditnote_form.html'
    success_url = 'payroll/credit/'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class DebitNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = DebitNote
    template_name = 'staff/payroll/debit_list.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class DebitNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = DebitForm
    template_name = 'staff/payroll/debitnote_form.html'
    success_url = '/payroll/debit'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class StartGeneratePayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'staff/payroll/salary.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if Payroll.objects.exists():
            context['messenger'] = f"Number of Records in Payroll: {Payroll.objects.count()}"
            last = Payroll.objects.all().last()
            context['last_period_generated'] = last.period
        else:
            context['messenger'] = 'No Record in Payroll Database'
        today = datetime.date.today()
        year = today.year
        month = today.month
        last_month = mytools.Month.last_month()
        next_month = mytools.Month.next_month()
        context['last_month'] = datetime.date(year, last_month, today.day).strftime('%B')
        context['this_month'] = today.strftime('%B')
        context['next_month'] = datetime.date(year, next_month, today.day).strftime('%B')
        context['last_period'] = f"{year}-{str(month-1).zfill(2)}"
        context['current_period'] = f"{year}-{str(month).zfill(2)}"
        context['next_period'] = f"{year}-{str(month+1).zfill(2)}"
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context=context)


class GeneratePayroll(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Generate payroll and save to Payroll model"""
    template_name = 'staff/payroll/generated_payroll.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        """This is not clear"""
        period = context['period']
        employees = Employee.active.all()
        (credit_amount,
         debit_amount,
         net_pay,
         deduction,
         outstanding,
         salary,
         tax) = (list(), list(), list(), list(), list(), list(), list())

        for employee in employees:
            salary.append(employee.basic_salary+employee.allowance)
            tax.append(employee.tax_amount)

            # cr_amount is the aggregate credit amount for a staff
            # yet to be taken
            obj_credit = CreditNote.objects.filter(period=period)
            obj_credit = obj_credit.filter(name=employee.id)
            cr_amount = sum(cr.value for cr in obj_credit)
            cr_amount = Money(0, 'NGN') if cr_amount == 0 else cr_amount
            credit_amount.append(cr_amount)

            # dr_amount is the aggregate debit amount for a staff
            # yet to be taken
            obj_debit = DebitNote.objects.filter(period=period)
            obj_debit = obj_debit.filter(name=employee.id)
            dr_amount = sum(dr.value for dr in obj_debit)
            dr_amount = Money(0, 'NGN') if dr_amount == 0 else dr_amount
            debit_amount.append(dr_amount)

            # the value to use to measure what we decide
            amount_to_pay = employee.gross_pay() + employee.balance + cr_amount - dr_amount

            # implement salary regime function to obtain net pay, deductions
            # and outstanding
            result = Salary.regime(amount_to_pay, employee.gross_pay())

            net_pay.append(result[0])
            deduction.append(result[1])
            outstanding.append(result[2])

        group = zip(employees,
                    salary,
                    tax,
                    credit_amount,
                    debit_amount,
                    net_pay,
                    deduction,
                    outstanding)
        totals = [
            # sum(record.salary().amount for record in employees),
            # sum(record.tax_amount.amount for record in employees),
            sum(i.amount for i in salary),
            sum(i.amount for i in tax),
            # sum(record.gross_pay().amount for record in employees),
            sum(record.balance.amount for record in employees),
            sum(i.amount for i in credit_amount),
            sum(i.amount for i in debit_amount),
            sum(i.amount for i in net_pay),
            sum(i.amount for i in deduction),
            sum(i.amount for i in outstanding)
        ]
        x = period.split('-')
        year = x[0]
        month = datetime.date(int(year), int(x[1]), 1).strftime('%B')
        #
        context = {
            "records": group,
            'period': period,
            'year': year,
            'month': month,
            'salary': totals[0],
            'tax': totals[1],
            'salary_due': totals[2],
            'balance': totals[2],
            'credit': totals[3],
            'debit': totals[4],
            'net_pay': totals[5],
            'deduction': totals[6],
            'outstanding': totals[7],
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        """Go into the payroll database and fetch data for the period"""
        queryset = Payroll.objects.filter(period=context['period'])

        if queryset.exists():
            context['object'] = queryset
            return render(request, 'staff/payroll/recordexists.html', context)

        return render(request, self.template_name, context)
        # return HttpResponse(f'{queryset}')

    def post(self, request, **kwargs):
        """Get context, get period"""
        context = self.get_context_data(**kwargs)

        """Save to database or throw error if data is unclean"""
        """record context is group"""
        for row in context['records']:
            staff = Employee.active.get(pk=int(row[0].id))
            """get the queryset"""
            data = Payroll(period=context['period'],
                           date_paid=datetime.date.today(),
                           staff=staff,
                           credit_amount=round(row[3], 2),
                           debit_amount=round(row[4], 2),
                           net_pay=round(row[5], 2),
                           deduction=round(row[6], 2),
                           outstanding=round(row[7], 2),
                           status=False,
                           # added two field as adjusted in model
                           salary=round(row[1], 2),
                           tax=round(row[2], 2),
                           )
            try:
                data.full_clean()
                data.save()  # Save Save Save
            except ValidationError as err:
                """send mail to admin"""
                return HttpResponse(f"""Generated data is not clean. 
                Check the validity of your 
                data and try again or contact your admin. {err}""")
            else:
                """generated outstanding in Payroll to replace balances in Employee"""
                staff.balance = data.outstanding
                staff.save()
        # end of loop #

        """Send mail to managers"""
        context.update({'user': request.user})
        mail_message = loader.render_to_string('staff/payroll/payroll_mail.html',
                                               context)

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
            cr_amount = sum(cr.value for cr in obj_credit)
            cr_amount = Money(0, 'NGN') if cr_amount == 0 else cr_amount

            # dr_amount is the aggregate debit amount
            obj_debit = DebitNote.objects.filter(period=period)
            obj_debit = obj_debit.filter(name=employee.id)
            dr_amount = sum(dr.value for dr in obj_debit)
            dr_amount = Money(0, 'NGN') if dr_amount == 0 else dr_amount

            # the value to use to measure what we decide
            amount_to_pay = employee.gross_pay() + employee.balance + cr_amount - dr_amount

            # implement salary regime function to obtain net pay, deductions
            # and outstanding
            data = Salary.regime(amount_to_pay, employee.gross_pay())

            staff_id = Employee.active.get(pk=employee.id)
            payroll = Payroll.objects.filter(period=period)
            staff, created = payroll.update_or_create(period=period,
                                                      staff=staff_id,
                                                      defaults={
                                                          'period': period,
                                                          'staff': staff_id,
                                                          'credit_amount': cr_amount,
                                                          'debit_amount': dr_amount,
                                                          'net_pay': data[0],
                                                          'deduction': data[1],
                                                          'outstanding': data[2],
                                                          # added fields
                                                          'salary': staff_id.basic_salary + staff_id.allowance,
                                                          'tax': staff_id.tax_amount,
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
    model = Payroll
    template_name = 'staff/payroll/start_pay.html'
    object_list = model.objects.filter(status=False)

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
        periods = []
        for i in self.object_list:
            if i.period not in periods:
                periods.append(i.period)
        context['periods'] = sorted(periods)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        period = context['periods'][-1]
        context['period'] = period
        context['object'] = self.object_list.filter(period=period)
        return render(request, self.template_name, context)

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        period = tuple(value for value in request.POST.items())
        period = period[-1][0]
        objects = self.object_list.filter(period=period)
        context['object'] = objects
        context['period'] = period
        return render(request, self.template_name, context)


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
        return context

    def post(self, request, pk):
        """The update of status, date paid and the alert message for successful payment"""
        staff = self.model.objects.get(pk=request.POST['pk'])
        staff.status = True
        staff.date_paid = datetime.date.today()
        staff.save()
        messages.success(request, f"{staff} paid successfully !!!",)
        return HttpResponseRedirect(reverse('start-pay'))


class PayrollStatement(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Payroll
    template_name = 'staff/payroll/statement.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        staff = Employee.active.get(id=kwargs['pk'])
        objects = self.model.objects.filter(staff=staff.id)

        context = {
            'code': kwargs['pk'],
            'objects': objects,
            'totals': 'list',
        }

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
        reassign = Reassign(staff=qs,
                            reassign_type=request.POST['type'],
                            from_position=request.POST['current_position'],
                            from_branch=request.POST['current_branch'],
                            to_position=request.POST['position'],
                            to_branch=request.POST['branch'],
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