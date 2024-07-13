import decimal
import calendar
import datetime
import json
import os
import time
from pathlib import Path
from typing import Any
from django.db.models.query import QuerySet

from django.forms import ValidationError
from survey.models import Question
from users.models import Profile
from apply.models import Applicant
from .models import (
    Employee, EmployeeBalance, CreditNote, DebitNote, Payroll, 
    Reassign, Terminate, Suspend, Permit,SalaryChange, 
    RequestPermission, Welfare
)
from .form import (DebitForm, CreditForm, EmployeeForm)
from core.models import JsonDataset
from django.contrib.auth.models import User
from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.views.generic import (View,
                                  TemplateView,
                                  ListView,
                                  DetailView,
                                  CreateView,
                                  UpdateView)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from djmoney.money import Money
from ozone import mytools
from decimal import Decimal
from django.contrib import messages
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.template import loader
from django.db.models import (F, Sum, Avg, Max, Min)


def duration(start_date, resume_date):
    if start_date.date() == resume_date.date():
        delta = (resume_date - start_date).total_seconds()
        # 1hr = 3600 seconds
        hours = int(divmod(delta, 3600)[0])
        return f'{hours}H'
    else:
        days = len(mytools.DateRange(start_date.date(), resume_date.date()).exclude_weekday(calendar.SUNDAY))
        return f'{days - 1}D'

# This is not a view class
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
        return [salary_payable, Money(0, 'NGN'), Money(0, 'NGN')]


# Views Classes
class StaffMainPageView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    template_name = 'staff/home_page.html'
    messages_one = """Employees remain the most important asset of this company.
Their combined effort is the result of what we have today. However, for the purpose of leadership and direction,
we must provide policies and procedures to guide everyone towards expected result. We believe in their collaborative
effort, integrity, punctuality and passion as they carry out their various assigned tasks. Therefore, whatever we do,
our staff comes first and only with them can we pride ourselves in what we have achieved. As a company, we believe every
staff deserves respect from one another irrespective of position and status and also from our clients while they 
discharge their duty to them. In as much as we have groomed them to treat our customers as Kings and Queens. The 
happiness of our staff is important, that is what we expect them to transfer to our customers and their fellow staff. 
"""
    messages_two = """The most important parameter we measure is employee engagement. Those who are discretionary,
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
        ids = Permit.objects.filter(staff__status=True).filter(starting_from__year=datetime.date.today().year).values_list('staff__pk', flat=True).distinct()
        permits = list()
        for id in ids:
            permits.append(Permit.objects.filter(starting_from__year=datetime.date.today().year).filter(staff__pk=id))
        
        permit_list = list()
        for permit in permits:
            hours, days = list(), list()
            for obj in permit:
                if obj.duration()[-1] == 'H':
                    hours.append(int(obj.duration().replace('H', '')))
                else:
                    days.append(int(obj.duration().replace('D', '')))
                
            h = divmod(sum(hours), 10) if sum(hours) > 0 else (0, 0)
            result = (sum(days) + h[0], h[1])
            
            permit_list.append({
                'code': obj.staff.pk,
                'name': obj.staff.fullname(),
                'duration': result,
                'count': permit.count()
                })
        
        if queryset.exists():
            for obj in queryset:
                countdown = mytools.DatePeriod.countdown(obj.staff.birth_date.strftime('%d-%m-%Y'), 10)
                if countdown >= 0:
                    data[obj.staff.first_name] = countdown

        if Reassign.objects.exists():
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
            'female': queryset.filter(staff__gender='FEMALE').count(),
            
            'message_two': self.messages_two,

            'management': queryset.filter(is_management=True).count(),
            'terminated': Employee.objects.filter(status=False).count(),
            
            'probation': queryset.filter(is_confirmed=False).count(),
            'internal_probation': len(recordset),

            'staff_on_probation': self.confirm_staff(),
            'reassign_data': recordset,
            'today': datetime.date.today(),
            'staff_category': 'terminate',
            'number_of_permissions': len(permit_list),
            'permissions': permit_list #Permit.objects.all().order_by('-starting_from')
        }
        
        return render(request, self.template_name, context=context)

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
        BASE_DIR = Path(__file__).resolve().parent.parent

        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as rf:
                content = json.load(rf)
                context['switch'] = content['switch']
        

        if self.queryset:
            employees = self.queryset.exclude(staff__last_name='Nwokoro')
            context['earliest_employee'] = employees.earliest('date_employed')
            context['latest_employee'] = employees.latest('date_employed')
            context['youngest_employee'] = employees.earliest('staff__birth_date')
            context['oldest_employee'] = employees.latest('staff__birth_date')
            context['highest_paid'] = employees.latest('basic_salary').basic_salary
            context['lowest_paid'] = employees.earliest('basic_salary').basic_salary
        return context

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
        
        permit = Permit.objects.filter(starting_from__year=datetime.date.today().year, staff_id=person)
        
        if permit.exists():
            days, hours = list(), list()
            for p in permit:
                if p.duration()[-1] == 'D':
                    days.append(int(p.duration()[:-1]))
                else:
                    hours.append(int(p.duration()[:-1]))
            consumed = (sum(days), sum(hours))
        else:
            consumed = (0, 0)

        balance = EmployeeBalance.objects.filter(staff_id=person)
        
        if balance.exists():
            credit = balance.filter(value_type='Cr')
            debit = balance.filter(value_type='Dr')
            credit_value = credit.aggregate(total=Sum('value'))['total'] if credit else Decimal('0')
            debit_value = debit.aggregate(total=Sum('value'))['total'] if debit else Decimal('0')
            total_balance = credit_value - debit_value
        else:
            total_balance = Decimal('0.00')

        welfare = Welfare.objects.filter(staff_id=person)

        if welfare.exists():
            total_welfare = welfare.aggregate(Sum('amount'))['amount__sum']
        else:
            total_welfare = Decimal('0.00')

        context['naira'] = chr(8358)
        user = User.objects.filter(username=f'{person.staff.first_name}-{str(person.id).zfill(2)}')
        if user.exists():
            context['username'] = user.get().get_username()
        context['permissible_days'] = int(leave)
        context['consumed_days'] = consumed
        context['permit_count'] = 'None' if consumed == (0, 0) else permit.count()
        # context['balance_days'] = int(leave) - days_consumed
        
        json_dict = JsonDataset.objects.get(pk=1).dataset
        
        context['positions'] = json_dict['positions']
        context['branches'] = json_dict['branches']
        
        context['reassigned'] = Reassign.objects.filter(staff_id=person)
        context['permissions'] = Permit.objects.filter(staff_id=person)
        context['suspensions'] = Suspend.objects.filter(staff_id=person)
        context['salary_changed'] = SalaryChange.objects.filter(staff_id=person)
        context['total_balance'] = total_balance
        context['total_welfare'] = total_welfare
        context['payout'] = Payroll.objects.filter(staff_id=self.kwargs['pk']).aggregate(total=Sum('net_pay'))['total']
        context['question_obj'] = Question.objects.filter(staff_id=person).first()
        
        dic = JsonDataset.objects.get(pk=2).dataset
        context['gratuity_title'] = dic['gratuity-title'][0]

        context['welfare_last_record'] = Welfare.objects.latest('date')
        qs = Welfare.objects.filter(date=context['welfare_last_record'].date)
        context['welfare_for_a_date'] = qs
        context['welfare_for_a_date_total_amount'] = qs.aggregate(Sum('amount'))['amount__sum']
        return context

    # queryset = Employee.active.all()

class StaffListPrivateView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Employee
    ordering = '-pk'
    template_name = 'staff/employee_list_private.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    
    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(status=True)
    
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

class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Employee
    form_class = EmployeeForm    
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    
    def get_context_data(self, **kwargs):
        applicant_obj = Applicant.objects.get(id=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['title'] = 'New'
        context['applicant_obj'] = applicant_obj
        return context
    
    
    def form_valid(self, form):
        applicant = Applicant.objects.get(id=self.kwargs['pk'])
        
        """Form data"""
        form.instance.staff = applicant
        # Approved salary shared to basic salary & allowance
        salary = float(form.cleaned_data['salary'].replace(',', ''))
        form.instance.basic_salary = 0.6 * salary
        form.instance.allowance = 0.4 * salary

        # change the applicant from pending to employed
        applicant.state = 'Employed'
        applicant.save()

        """Send mail to applicant and admin before overwriting save"""
        return super().form_valid(form)
        
class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee
    fields = ['image']

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

class AddGratuity(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        staff = get_object_or_404(Employee.active, pk=kwargs['pk'])
        """Create a record of this balance"""
        value = float(request.POST.get('balance')) if request.POST.get('balance') != '' else Money(0, 'NGN')
        balance = EmployeeBalance.objects.create(staff=staff,
                                                 value=value,
                                                 value_type=request.POST.get('CrDr'),
                                                 description=request.POST.get('comment'),
                                                 title=request.POST.get('title')
                                                 )
        balance.save()
        messages.success(request, 'Profile Balance changed successfully !!!')
        return redirect(staff)

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
        
        qs.basic_salary = Money(0.4 * salary, 'NGN')
        qs.allowance = Money(0.6 * salary, 'NGN')
        qs.save()

        change_salary = SalaryChange(staff=person,
                                     previous_value=previous_pay,
                                     value=Money(salary, 'NGN'),
                                     remark=request.POST['remark']
                                     )
        change_salary.save()
        messages.success(request, f"Salary Change is successful")
        return redirect('employee-detail', pk=kwargs['pk'])

class StaffChangeManagement(View):
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if request.POST['mgmtStaff'] == 'on':
            obj = get_object_or_404(Employee, pk=kwargs['pk'])
            obj.is_management = True
            obj.save()
            messages.success(request, 'Change made successfully !!!')
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
        
        period = mytools.DatePeriod.working_days(start_date_object, ending_at_object)

        if period == -1:
            messages.info(request, f'Permission cannot be granted on a backward date. Check your date selection')
        else:
            if period[0] == 0:
                messages.success(request, f'Permission Granted for {period[1]} Hour(s)')
                permit.save()
                send_mail("Grant Permission",
                 f'''Permission has been granted to {person} for {period[1]} Hour(s).
                 Resumption date is {ending_at_object.strftime("%d-%B-%Y")}.''', 
                from_email='',
                recipient_list=['ogechukwu.okpala@ozonefl.com', 'uzo.nwokoro@ozonefl.com'],
                fail_silently=True,
                )
            else:
                messages.success(request, f'Permission Granted for {period[0]} Day(s)')
                permit.save()
                send_mail('Grant Permission', 
                f'''Permission has been granted to {person} for {period[0]} Days(s).
                Resumption date is {ending_at_object.strftime("%d-%B-%Y")}.''',
                from_email='',
                recipient_list=['ogechukwu.okpala@ozonefl.com', 'uzo.nwokoro@ozonefl.com'],
                fail_silently=True,
                )
        return redirect('employee-detail', pk=kwargs['pk'])

class RequestPermissionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, **kwargs):
        staff = get_object_or_404(Employee, pk=kwargs['pk'])
        start_date = datetime.datetime.strptime(request.POST['startFrom'], '%Y-%m-%dT%H:%M')
        resume_date = datetime.datetime.strptime(request.POST['endingAt'], '%Y-%m-%dT%H:%M')
        if resume_date > start_date:
            permission = RequestPermission(
                request_by=request.user,
                staff=staff,
                reason=request.POST['reason'],
                start_date=start_date,
                resume_date=resume_date
            )
            permission.save()
            messages.success(request, f"permission has been requested. Approval will be required to GRANT IT")
            email = EmailMessage(
                subject=f'Permission Request ID - {str(permission.pk).zfill(3)}',
                body=loader.render_to_string('mail/request_permission.html', context={'object': permission, 'title': 'Permission'}),
                from_email='',
                to=['uzo.nwokoro@ozonefl.com', f'{permission.request_by.email}'],  
            )
            email.content_subtype="html"
            email.send(fail_silently=False)
        else:
            messages.warning(request, f"Start date cannot be greater than end date. REQUESTED UNSUCCESSFUL")
        return redirect(staff)

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
            employee = self.get_queryset().get(id=kwargs['pk'])
            employee.status = False
            employee.save()

            """Create a terminate record"""
            term = Terminate(staff=employee,
                             termination_type=request.POST['type'],
                             remark=request.POST['remark'],
                             date=request.POST['date'])
            term.save()

            employee.staff.state = 'Resigned' if term.termination_type == 'Resign' else 'Sacked'
            employee.staff.save()    

            """success message"""
            messages.success(request, f"{employee} with ID {str(employee.pk).zfill(3)} is terminated successfully")
            return redirect('staff-list')

        messages.info(request, "Incorrect key word, Staff yet to be terminated")
        return redirect('employee-detail', pk=kwargs['pk'])

class staffWelfare(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Employee

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def post(self, request, *args, **kwargs):
        person = self.get_queryset().get(id=kwargs['pk'])
        date = datetime.datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
        
        welfare = Welfare(
            staff=person,
            date=date,
            description=request.POST['description'],
            amount=float(request.POST['amount'])
        )
        welfare.save()
        
        messages.success(request, f'Welfare support saved successfully !!!')
        return redirect('employee-detail', pk=kwargs['pk'])

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
        period = kwargs['object'].period
        # month = int(period.split('-')[1])

        # balance = EmployeeBalance.objects.filter(staff=staff).filter(date__month=month).aggregate(total=Sum('value'))['total']
        # balance = decimal.Decimal('0') if balance is None else balance

        cr = EmployeeBalance.objects.filter(staff=staff, period=period, value_type='Cr').aggregate(Sum('value'))['value__sum']
        dr = EmployeeBalance.objects.filter(staff=staff, period=period, value_type='Dr').aggregate(Sum('value'))['value__sum']
        Cr = decimal.Decimal('0') if cr is None else cr
        Dr = decimal.Decimal('0') if dr is None else dr
            

        context['balance'] = Cr - Dr
        
        return context

    def post(self, request, pk):
        """The update of status, date paid and the alert message for successful payment"""
        staff = self.model.objects.get(pk=pk)
        staff.status = True
        staff.date_paid = datetime.date.today()
        staff.save()
        messages.success(request, f"{staff} paid successfully !!!")
        return redirect(reverse('start-pay'))

class PayslipStatement(LoginRequiredMixin, UserPassesTestMixin, DetailView):
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
        payslip = self.get_queryset().filter(staff=staff.id)
        
        context['code'] = kwargs['pk']
        context['objects'] = payslip
        context['totals'] = 'list'
        return render(request, self.template_name, context=context)    

class GratuityListViewOneStaff(ListView):
    # template_name = 'staff/balance.html'

    def get_queryset(self):
        return EmployeeBalance.objects.filter(staff_id=self.kwargs['pk']).order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cr = self.get_queryset().filter(value_type='Cr').aggregate(total=Sum('value'))['total']
        dr = self.get_queryset().filter(value_type='Dr').aggregate(total=Sum('value'))['total']
        cr = cr if cr is not None  else Decimal('0')
        dr = dr if dr is not None else Decimal('0')
        context['total_value'] = cr - dr
        context['return'] = 'detail'
        return context

class UserHandleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    fields = []
    
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='Administrator').exists():
            return True
        return False

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = get_object_or_404(Employee, pk=self.kwargs['pk'])
        context['staff'] = staff
        context['username'] = f'{staff.staff.first_name}-{str(staff.id).zfill(2)}'
        context['first_name'] = staff.staff.first_name
        context['last_name'] = staff.staff.last_name
        context['email'] =  staff.staff.email if staff.official_email is None else staff.official_email 
        return context
    
    
    def form_valid(self, form):
        global password
        staff = get_object_or_404(Employee, pk=self.kwargs['pk'])
        form.instance.username = f'{staff.staff.first_name}-{str(staff.id).zfill(2)}'
        form.instance.first_name = staff.staff.first_name
        form.instance.last_name =  staff.staff.last_name
        form.instance.email = staff.staff.email if staff.official_email is None else staff.official_email
        password = User.objects.make_random_password()
        context = {
            'header': 'SCusH login credential created',
            'username': form.instance.username,
            'password': password,
            'first_name': form.instance.first_name,
            'last_name': form.instance.last_name,
            'email': form.instance.email,
        }
        email = EmailMessage(
            subject=f"User handle Created for {staff}",
            body=loader.render_to_string('mail/user_create.html', context), 
            from_email='',
            to=[form.instance.email],
            cc=['uzo.nwokoro@ozonefl.com', 'dickson.abanum@ozonefl.com'],
        )
        email.content_subtype='html'
        email.send(fail_silently=True)
        return super().form_valid(form)
    

    def get_success_url(self):
        user_profile = Profile.objects.last()
        user = User.objects.last()
        user_profile.staff = get_object_or_404(Employee, pk=self.kwargs['pk'])
        user.set_password(password)
        user.save()
        user_profile.save()
        return reverse("employee-detail", kwargs={'pk': self.kwargs['pk']})

class TerminatedStaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    queryset = Terminate.objects.filter(status=True)
    template_name = 'staff/staff_views.html'
    ordering = '-date'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sacked'] = self.get_queryset().filter(termination_type='Sack').count()
        context['resigned'] = self.get_queryset().filter(termination_type='Resign').count()
        
        return context

# Payroll Section
class PayrollHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'staff/payroll/salary.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = datetime.date.today()
        
        payroll = Payroll.objects.all()
        
        if payroll.exists():
            last = Payroll.objects.last()

            """If payroll record exist, then get the last record's period and convert to integer"""
            month_in_period = int(last.period.split('-')[1])
            year_in_period = int(last.period.split('-')[0])
            
            context['last_period_generated'] = f'{calendar.month_name[month_in_period]}, {year_in_period}'
            context['next_period'] = mytools.Period(year_in_period, month_in_period).next()
            context['payroll_current_period'] = Payroll.objects.last().period
            #payout, welfare & gratuity
            context['payout_total'] = payroll.aggregate(Sum('net_pay'))['net_pay__sum']
            context['payout_current_year'] = payroll.filter(period__contains=year_in_period).aggregate(Sum('net_pay'))['net_pay__sum']
            context['payout_year'] = year_in_period
            context['gratuity'] = EmployeeBalance.objects.aggregate(Sum('value'))['value__sum']
            context['welfare'] = Welfare.objects.aggregate(Sum('amount'))['amount__sum']
        else:
            context['next_period'] = f'{today.year}-{str(today.month).zfill(2)}'
        next_month = context['next_period'].split('-')[1]
        the_year = context['next_period'].split('-')[0]

        context['next_month'] = mytools.Period.full_months[next_month]
        context['the_year'] = the_year

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.GET:
            period = request.GET['period']
            return redirect('generate-payroll', period=period)
        return render(request, self.template_name, context=context)


class CreditNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CreditNote
    template_name = 'staff/payroll/creditnote_list.html'
    ordering = '-pk'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = self.get_queryset().aggregate(Sum('value'))['value__sum']
        return context
    
    
    def get_queryset(self):
        qs = CreditNote.objects.all()
        if qs.exists():
            period = CreditNote.objects.latest('credit_date').period
            return super().get_queryset().filter(period=period)
        return super().get_queryset()


class CreditDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = CreditNote
    template_name = 'staff/payroll/creditnote_detail.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    

class CreditUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CreditNote
    form_class = CreditForm
    template_name = 'staff/payroll/creditnote_form.html'
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    
    def get_success_url(self):
        return reverse_lazy('credit-detail', kwargs={'pk': self.kwargs['pk']})


class CreditNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CreditForm
    template_name = 'staff/payroll/creditnote_form.html'
    
    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    
    def get_success_url(self):
        if self.request.POST['action'] == '1':
            time.sleep(3)
            return reverse_lazy('credit-create')
        return reverse_lazy('salary')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        BASE_DIR = Path(__file__).resolve().parent.parent
        file_path = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as rf:
                json_data = json.load(rf)
            if json_data['switch'] == 2:
                context['switch'] = 2
                context['payroll_url'] = reverse('payroll-process')
        return context

        
class DebitNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = DebitNote
    template_name = 'staff/payroll/debitnote_list.html'
    ordering = '-pk'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_queryset(self):
        qs = DebitNote.objects.all()
        if qs.exists():
            period = DebitNote.objects.latest('debit_date').period
            return super().get_queryset().filter(period=period)
        return super().get_queryset()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = self.get_queryset().aggregate(Sum('value'))['value__sum']
        return context


class DebitUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = DebitNote
    form_class = DebitForm
    template_name = 'staff/payroll/debitnote_form.html'
    
    def get_success_url(self):
        return reverse_lazy('debit-detail', kwargs={'pk': self.kwargs['pk']})

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False
    

class DebitNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = DebitForm
    template_name = 'staff/payroll/debitnote_form.html'
    # success_url = reverse_lazy('salary')

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_success_url(self):
        if self.request.POST['action'] == '1':
            time.sleep(3)
            return reverse_lazy('debit-create')
        return reverse_lazy('salary')
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        BASE_DIR = Path(__file__).resolve().parent.parent
        file_path = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as rf:
                json_data = json.load(rf)
            if json_data['switch'] == 2:
                context['switch'] = 2
                context['payroll_url'] = reverse('payroll-process')
        return context


class DebitNoteDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = DebitNote
    template_name = 'staff/payroll/debitnote_detail.html'

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False


class TaxList(LoginRequiredMixin, ListView):
    model = Employee
    
    def get_queryset(self):
        return super().get_queryset().filter(status=True)

    def get_template_names(self):
        
        return ['staff/payroll/tax_list.html']


class UpdateTax(LoginRequiredMixin, UpdateView):
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
        years = [str(this_year), str(this_year-1)]
        context = {
            'title': 'view payroll',
            'heading': {'year': year, 'month': mytools.Period.full_months.get(month)},
            'payroll': self.get_queryset().filter(period=period).order_by('-staff'),
            'salary': self.get_queryset().filter(period=period).aggregate(sum=Sum('net_pay')),
            'naira': chr(8358),
            'periods_months': self.recent_months(self.get_queryset().last().period),
            'months': mytools.Period.full_months,
            'years': years,
            'summary_period': ('Month', 'Year')
        }
        return render(request, self.template_name, context=context)


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
        # data['balance'] = queryset.aggregate(total=Sum('balance'))
        data['salary'] = queryset.aggregate(total=Sum('salary'))
        data['tax'] = queryset.aggregate(total=Sum('tax'))
        data['credit'] = queryset.aggregate(total=Sum('credit_amount'))
        data['debit'] = queryset.aggregate(total=Sum('debit_amount'))
        data['net_pay'] = queryset.aggregate(total=Sum('net_pay'))
        return data

    def get(self, request, *args, **kwargs):
        """Search the database for all periods
        and use set to filter out repeated periods"""
        periods = self.get_queryset().values_list('period', flat=True).distinct()
        dataset = list()
        if kwargs.get('summary_period') == 'Month':
            if request.GET == {}:
                year = datetime.date.today().year
            else:
                year = int(request.GET['year'])
            periods = periods.filter(period__contains=year)
            for period in sorted(periods):
                queryset = self.get_queryset().filter(period=period)
                qs_dict = self.get_dict(queryset)
                qs_dict['period'] = mytools.Period.full_months.get(period.split('-')[1])
                dataset.append(qs_dict) 
        else:
            year_set = set(i.split('-')[0] for i in periods)
            for year in sorted(year_set):
                queryset = self.get_queryset().filter(period__startswith=year)
                qs_dict = self.get_dict(queryset)
                qs_dict['period'] = year
                dataset.append(qs_dict)
                
        totals = (
            sum(obj['salary']['total'] for obj in dataset),
            sum(obj['tax']['total'] for obj in dataset),
            sum(obj['credit']['total'] for obj in dataset),
            sum(obj['debit']['total'] for obj in dataset),
            sum(obj['net_pay']['total'] for obj in dataset)
        )

        context = {
            'title': kwargs.get('summary_period'),
            'current_period': self.get_queryset().last().period,
            'dataset': tuple(dataset),
            'totals': totals,
            'years': [str(datetime.date.today().year - i) for i in range(3)],
            'year': str(year)
        }
        return render(request, 'staff/payroll/payroll_summary.html', context)


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
        employees = Employee.active.all()

        data = list()
        for employee in employees:
            record = dict()
            # cr_amount is the aggregate credit amount for a staff
            # yet to be taken
            obj_credit = CreditNote.objects.filter(period=kwargs['period']).filter(name=employee.id)
            cr_amount = obj_credit.aggregate(total=Sum('value'))
            cr_amount['total'] = Money('0.00', 'NGN') if cr_amount['total'] is None else Money(cr_amount['total'], 'NGN')

            # dr_amount is the aggregate debit amount for a staff
            # yet to be taken
            obj_debit = DebitNote.objects.filter(period=kwargs['period']).filter(name=employee.id)
            dr_amount = obj_debit.aggregate(total=Sum('value'))
            dr_amount['total'] = Money('0.00', 'NGN') if dr_amount['total'] is None else Money(dr_amount['total'], 'NGN')

            # the value to use to measure what we decide
            net_pay = employee.gross_pay() + cr_amount['total'] - dr_amount['total']
            
            record['code'] = employee.id
            record['staff'] = employee.fullname()
            record['salary'] = employee.salary()
            record['tax'] = employee.tax_amount
            record['gross_pay'] = employee.gross_pay()
            record['credit'] = cr_amount['total']
            record['debit'] = dr_amount['total']
            record['earning'] = net_pay
            data.append(record)

        year = kwargs['period'].split('-')[0]
        month = datetime.date(int(year), int(kwargs['period'].split('-')[1]), 1).strftime('%B')

        context["naira"] = chr(8358)
        context["records"] = data
        context['period'] = kwargs['period']
        context['year'] = year
        context['month'] = month

        # The totals
        context['salary'] = sum(i['salary'] for i in data)
        context['tax'] = sum(i['tax'] for i in data)
        context['gross_pay'] = sum(i['gross_pay'] for i in data)
        context['credit'] = sum(i['credit'] for i in data)
        context['debit'] = sum(i['debit'] for i in data)
        context['net_pay'] = sum(i['earning'] for i in data)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        """Go into the payroll database and fetch data for the period"""
        queryset = Payroll.objects.filter(period=context['period'])

        if queryset.exists():
            context['object'] = queryset
            context['payout'] = queryset.aggregate(total=Sum('net_pay'))['total']
            context['wages'] = queryset.aggregate(total=Sum('salary'))['total']
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
                           credit_amount=round(row['credit'], 2),
                           debit_amount=round(row['debit'], 2),
                           net_pay=round(row['earning'], 2),
                           status=False,
                           )
            try:
                data.full_clean()
                data.save()  # Save Save Save
            except ValidationError as err:
                """send mail to admin"""
                return HttpResponse(f"""
                Generated data is not clean. 
                Check the validity of your 
                data and try again or contact your admin. {err}.
                """)
            
        # end of loop #

        """Send mail to managers"""
        context.update({'user': request.user})
        mail_message = loader.render_to_string('staff/payroll/payroll_mail.html', context)

        send_mail(
            f"Payroll Generated for {context['month']}, {context['year']}",
            message="",
            fail_silently=False,
            from_email='',
            recipient_list=['uzo.nwokoro@ozonefl.com'],
            html_message=mail_message
            )
        return render(request, 'staff/payroll/payroll_reports.html', context)


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
        periods = qs.values_list('period', flat=True).distinct().order_by('-period')

        periods = periods[:4] if len(periods) > 4 else periods

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
        """get the records you want to replace with payroll data
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


class StaffPoliciesView(TemplateView):
    template_name = 'staff/policies.html'


class GratuityListView(ListView):
    model = EmployeeBalance
    ordering = ['-date']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cr = self.get_queryset().filter(value_type='Cr').aggregate(total=Sum('value'))['total']
        dr = self.get_queryset().filter(value_type='Dr').aggregate(total=Sum('value'))['total']
        cr = cr if cr is not None  else Decimal('0')
        dr = dr if dr is not None else Decimal('0')
        context['total_value'] = cr - dr

        
        # list of active staff that has earned gratuity
        active_staff = self.get_queryset().filter(staff__status=True).values_list('staff', flat=True).distinct().order_by()

        # the active staff queryset
        qs_active = list((staff, self.get_queryset().filter(staff=staff)) for staff in active_staff)

        active_staff_data = list()
        for qss in qs_active:
            
            active_dic = {
                'id': qss[0],
                'staff': Employee.objects.filter(pk=qss[0]).first().fullname,
                'credit': qss[1].filter(value_type='Cr').aggregate(Sum('value'))['value__sum'],
                'debit': qss[1].filter(value_type='Dr').aggregate(Sum('value'))['value__sum'],
                }
            active_staff_data.append(active_dic)
        
        context['active_staff'] = active_staff_data

        # list of terminated staff
        term_staff = self.get_queryset().filter(staff__status=False).values_list('staff', flat=True).distinct().order_by()

        # the terminated staff queryset in gratuity
        qs_term = list((staff, self.get_queryset().filter(staff=staff)) for staff in term_staff)

        term_staff_data = list()
        for qss in qs_term:
            term_dic = {
                'id': qss[0],
                'staff': Employee.objects.get(pk=qss[0]).fullname,
                'credit': qss[1].filter(value_type='Cr').aggregate(Sum('value'))['value__sum'],
                'debit': qss[1].filter(value_type='Dr').aggregate(Sum('value'))['value__sum'],
                }
            term_staff_data.append(term_dic)
            
        context['term_staff'] = term_staff_data
        return context


class GratuityListViewOneStaff(LoginRequiredMixin, TemplateView):

    template_name = 'staff/gratuity/employee_gratuity_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 
        
        context['staff'] = Employee.objects.get(id=kwargs['pk'])
        staff_gratuity = EmployeeBalance.objects.filter(staff=kwargs['pk'])
        context['staff_gratuity'] = staff_gratuity
        value = staff_gratuity.filter(value_type='Cr').aggregate(Sum('value'))['value__sum']
        credit_amount = value if value is not None else decimal.Decimal('0')
        value = staff_gratuity.filter(value_type='Dr').aggregate(Sum('value'))['value__sum']
        debit_amount = value if value is not None else decimal.Decimal('0')
        context['net_value'] = credit_amount - debit_amount
        return context


class GratuityDetailView(DetailView):
    model = EmployeeBalance


class GratuityUpdateView(UpdateView):
    model = EmployeeBalance
    fields = '__all__'
    
    def get_success_url(self):
        return reverse_lazy('employee-balance-detail', kwargs={'pk': self.kwargs['pk']})


class RequestPermissionListView(LoginRequiredMixin, ListView):
    model = RequestPermission
    ordering = '-pk'   
    template_name = 'staff/request_permission_list.html' 

    def get_queryset(self):
        return super().get_queryset().filter(status=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # get the list of all the staff that have taken permission this year
        staff_taken_permission = Permit.objects.filter(staff__status=True).values_list('staff__pk', flat=True).distinct()
        staff_list = list()
        for staff in staff_taken_permission:
            staff_list.append(Permit.objects.filter(staff__pk=staff))
        
        permit_list = list()
        for permit in staff_list:
            hours, days = list(), list()
            for obj in permit:
                if obj.duration()[-1] == 'H':
                    hours.append(int(obj.duration().replace('H', '')))
                else:
                    days.append(int(obj.duration().replace('D', '')))
                
            h = divmod(sum(hours), 10) if sum(hours) > 0 else (0, 0)
            result = (sum(days) + h[0], h[1])
            
            permit_list.append({
                'code': obj.staff.pk,
                'name': obj.staff.fullname(),
                'duration': result,
                'count': permit.count()
                })
        context['permissions'] = permit_list
        return context


class RequestPermissionUpdateView(LoginRequiredMixin, UpdateView):
    model = RequestPermission
    fields = '__all__'
    # form_class = RequestPermissionForm
    template_name = 'staff/request_permission_form.html'

    
    def get(self, request, *args, **kwargs):
        request = RequestPermission.objects.get(pk=kwargs['pk'])
        self.initial['start_date'] = request.start_date
        self.initial['resume_date'] = request.resume_date
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form, **kwargs):

        durations = duration(form.instance.start_date, form.instance.resume_date)
        context = self.get_context_data(**kwargs)
        context['heading'] = f'Permission for {form.instance.staff} modified'
        context['object'] = {
            'request_by': self.request.user,
            'staff': form.instance.staff,
            'date': form.instance.date,
            'reason': form.instance.reason,
            'start_date': form.instance.start_date,
            'resume_date':form.instance.resume_date,
            'status': form.instance.status,
            'duration': (durations[:-1], durations[-1])
        }
        requester_email = form.instance.request_by.email
        mail_message = loader.render_to_string('mail/permission.html', context)

        send_mail(
            subject=f'Permission Request ID - #{str(self.kwargs["pk"]).zfill(3)}',
            message=f'Request for permission has been modified from {form.instance.start_date} to {form.instance.resume_date} for {form.instance.staff}.',
            from_email='',
            recipient_list=[self.request.user.email, requester_email, 'uzo.nwokoro@ozonefl.com', 'dickson.abanum@ozonefl.com'],
            fail_silently=True,
            html_message=mail_message
        )
        return super().form_valid(form, **kwargs)


class PermissionFromRequest(LoginRequiredMixin, CreateView):
    model = Permit
    fields = []

    def get(self, request, *args, **kwargs):
        self.object = get_object_or_404(RequestPermission, pk=self.kwargs['pk'])
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['code'] = self.kwargs.get('pk')
        context['object'] = get_object_or_404(RequestPermission, pk=self.kwargs['pk'])
        return context

    
    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        
        """The request to change to approved status"""
        obj = get_object_or_404(RequestPermission, pk=self.kwargs['pk'])
        obj.status = True
        obj.save()

        """Programmatically filling the form"""
        form.instance.staff = obj.staff
        form.instance.starting_from = obj.start_date
        form.instance.ending_at = obj.resume_date
        form.instance.reason = obj.reason

        messages.info(self.request, f'Permission Granted to {form.instance.staff} on request #{str(obj.id).zfill(3)}')
        
        requester_email = obj.request_by.email
        obj.refresh_from_db()
        context['object'] = obj 
        context['heading'] = f'Permission for {obj.staff} Decision'
        mail_message = loader.render_to_string('mail/permission.html', context)

        send_mail(f"Permission Request ID - {str(obj.pk).zfill(3)}",
        message=f'Permission Granted to {obj.staff} on request #{str(obj.id).zfill(3)}. {obj.reason} being the reason. Permitted on {obj.start_date} to resume on {obj.resume_date}',
        from_email='',
        recipient_list=[requester_email, 'uzo.nwokoro@ozonefl.com', 'dickson.abanum@ozonefl.com'],
        fail_silently=True,
        html_message=mail_message
        )        
        return super().form_valid(form, **kwargs)


class RequestPermissionDisapprove(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        context = {}
        obj = get_object_or_404(RequestPermission, pk=kwargs['pk'])
        obj.status = False
        obj.save()

        messages.info(request, f"Permission Request #{str(kwargs['pk']).zfill(3)} DISAPPROVED")
        
        context['heading'] = f'Permission for {obj.staff} Decision'
        obj.refresh_from_db()
        context['object'] = obj
        mail_message = loader.render_to_string('mail/permission.html', context)

        send_mail(subject=f"Permission Request ID - {str(obj.pk).zfill(3)}",
        message="Your request for permission is NOT APPROVED",
        from_email='',
        recipient_list=[obj.request_by.email, 'uzo.nwokoro@ozonefl.com', 'dickson.abanum@ozonefl.com'],
        fail_silently=True,
        html_message=mail_message
        )
        return redirect('request-permission-list')

# Not connected
class MakeOutstandingValueZero(View):

    def get(self, request, pk):
        staff = get_object_or_404(Payroll, pk=pk)
        new_pay = staff.net_pay + staff.outstanding
        staff.outstanding = Money(0, 'NGN')
        staff.net_pay = new_pay
        staff.save()
        return redirect(reverse('payroll-modify'))
  

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


class WelfareSupportList(LoginRequiredMixin, TemplateView):

    template_name = 'staff/welfare_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        codes = Welfare.objects.values_list('staff__id', flat=True).distinct()
        welfare_dataset = []
        for code in codes:
            qs = Welfare.objects.filter(staff__id=code)

            dic = {
                'id': code,
                'staff': qs.first().staff.staff,
                'amount': qs.aggregate(Sum('amount'))['amount__sum'],
                'count': qs.count()
            }
            welfare_dataset.append(dic)
        context['welfare_dataset'] = welfare_dataset 
        context['total'] = Welfare.objects.aggregate(Sum('amount'))['amount__sum']
        
        return context


class WelfareSupportListViewOneStaff(LoginRequiredMixin, ListView):
    model = Welfare
    template_name = 'staff/welfare_list_detail.html'

    def get_queryset(self):
        return super().get_queryset().filter(staff__id=self.kwargs['pk'])

# Payroll process developer code
class PayrollView(LoginRequiredMixin, TemplateView):
    template_name = 'staff/payroll/payroll.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build paths inside the project like this: BASE_DIR / 'subdir'.
        BASE_DIR = Path(__file__).resolve().parent.parent

        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        if not os.path.exists(filepath):
            # Point of entry
            employees = Employee.objects.all()
            context['employees'] = employees
            employees = employees.annotate(salary=F('basic_salary') + F('allowance'))
            context['totals'] = (employees.aggregate(Sum('salary'))['salary__sum'],
                                 employees.aggregate(Sum('tax_amount'))['tax_amount__sum']
                                )
            # create a json file (switch: 1 and employee_update: True)
            with open(filepath, 'w') as wf:
                data = {'switch': 1}
                json.dump(data, wf)
            context['switch'] = 0
        else:
            # open a json file to bring in data
            with open(filepath, 'r') as rf:
                data = json.load(rf)
            switch = data['switch']
            
            if switch == 1:
                if 'employeeUpdate' in self.request.GET:
                    data['employee_update'] = self.request.GET['employeeUpdate']
            
                # write data back into json
                with open(filepath, 'w') as wf:
                    json.dump(data, wf, indent=2)
                # data to template
                context['switch'] = switch
                context['employee_update'] = data['employee_update']
            elif switch == 2:
                # with open(filepath, 'r') as rf:
                #     json_data = json.load(rf)
                context['switch'] = 2
            elif switch == 3:
                context['switch'] = switch + 1
                # with open(filepath, 'r') as rf:
                #     content = json.load(rf)
                    
            else:
                os.remove(filepath)    
                context['switch'] = f'{switch} - process complete' 
        return context
    

class BackView(LoginRequiredMixin, View):
    def get(self, request):
        BASE_DIR = Path(__file__).resolve().parent.parent
        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        if os.path.exists(filepath):
            os.remove(filepath)    
        return redirect('payroll-process')

class NextView(LoginRequiredMixin, View):
    def get(self, request):
        BASE_DIR = Path(__file__).resolve().parent.parent
        filepath = os.path.join(BASE_DIR, 'core', f'{self.request.user}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as rf:
                json_data = json.load(rf)
                json_data['switch'] = 2
            with open(filepath, 'w') as wf:
                json.dump(json_data, wf, indent=2)
            
        return redirect('payroll-process')    

class ProcessEmployeeUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'staff/payroll/employee_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        return context
    