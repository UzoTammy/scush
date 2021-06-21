from .models import (Employee,
                     Payroll,
                     CreditNote,
                     DebitNote)
from django.shortcuts import render, reverse
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import (TemplateView,
                                  ListView,
                                  DetailView,
                                  CreateView,
                                  UpdateView,
                                  DeleteView)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apply.models import Applicant
from djmoney.money import Money
from ozone import mytools
import datetime
from django.contrib import messages
from django.contrib.auth.admin import Group
from django.core.mail import send_mail, mail_admins, mail_managers
from django.core.validators import ValidationError
from .form import DebitForm, CreditForm
from django.template import loader


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


class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Employee
    ordering = 'staff__first_name'
    queryset = model.active.all()

    def test_func(self):
        """if user is a member of of the group HRD then grant access to this view"""
        if self.request.user.groups.filter(name='HRD').exists():
            return True
        return False

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)

        """requires if data exist for query"""
        data = {}
        if self.queryset:
            for obj in self.queryset:
                countdown = mytools.DatePeriod.countdown(obj.staff.birth_date.strftime('%d-%m-%Y'), 10)
                if countdown >= 0:
                    data[obj.staff.first_name] = countdown
            context['countdown'] = sorted(data.items(), key=lambda x: x[-1])
            employees = self.queryset.exclude(position='MD')
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
         outstanding) = (list(), list(), list(), list(), list())

        for employee in employees:
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
                    credit_amount,
                    debit_amount,
                    net_pay,
                    deduction,
                    outstanding)
        totals = [
            sum(record.salary().amount for record in employees),
            sum(record.tax_amount.amount for record in employees),
            sum(record.gross_pay().amount for record in employees),
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

        context = {
            "records": group,
            'period': period,
            'year': year,
            'month': month,
            'salary': totals[0],
            'tax': totals[1],
            'salary_due': totals[2],
            'balance': totals[8],
            'credit': totals[4],
            'debit': totals[5],
            'net_pay': totals[6],
            'deduction': totals[7],
            'outstanding': totals[8],
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

    def post(self, request, **kwargs):
        """Get context, get period"""
        context = self.get_context_data(**kwargs)

        """Save to database or throw error if data is unclean"""
        for row in context['records']:
            staff = Employee.active.get(pk=int(row[0].id))
            """get the queryset"""
            data = Payroll(period=context['period'],
                           date_paid=datetime.date.today(),
                           staff=staff,
                           credit_amount=round(row[1], 2),
                           debit_amount=round(row[2], 2),
                           net_pay=round(row[3], 2),
                           deduction=round(row[4], 2),
                           outstanding=round(row[5], 2),
                           status=False)
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

