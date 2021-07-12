import datetime
from django.http import HttpResponse
from pdf.utils import render_to_pdf
from customer.models import CustomerProfile
from apply.models import Applicant
from django.contrib.auth.models import User
from django.views.generic import (View, ListView, TemplateView)
from staff.models import Employee, Payroll
from stock.models import Product
from django.db.models import Sum
from django.contrib.auth.mixins import LoginRequiredMixin


class CustomerView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query_set = CustomerProfile.objects.all()
        context = {
            'today': datetime.datetime.now(),
            'host': f"{request.META.get('HTTP_HOST')} | {request.user}",
            'users': User.objects.all(),
            'customers': query_set,
            'last_modified_object': query_set.latest('date_modified'),
            'last_time_modified': query_set.latest('date_modified').date_modified.strftime('%a, %d %b %Y %H:%M:%S WAT')
        }
        pdf = render_to_pdf('pdf/pdf_customer_list.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f'invoice_{context.get("order_id")}.pdf'
            content = f"inline; {filename}"
            download = request.GET.get('download')
            if download:
                content = f"attachment; {filename}"
            response['Content-Disposition'] = content
            return response
        return HttpResponse("invoice not found")


class PayrollListView(LoginRequiredMixin, ListView):
    model = Payroll
    template_name = 'pdf/pdf_payroll.html'
    context_object_name = 'employees'

    def get(self, request, *args, **kwargs):
        period = self.request.GET.get('period')
        queryset = self.get_queryset().filter(period=period)
        if queryset.exists():
            if period:
                p = period.split('-')
                year = int(p[0])
                month = int(p[1])
                month_word = datetime.date(year, month, 1).strftime("%B")
                period_word = f"{month_word}, {year}"
            else:
                period_word = ''

            context = {
                'N': 'NGN',
                'credentials': f"Authorized by: {request.user.first_name} {request.user.last_name}",
                'today': datetime.datetime.now(),
                'period': period,
                'period_month': period_word,
                'employees': queryset.order_by('staff'),
                'total_net_pay': queryset.aggregate(sum=Sum('net_pay')),
                'total_debit': queryset.aggregate(sum=Sum('debit_amount')),
                'total_credit': queryset.aggregate(sum=Sum('credit_amount')),
                'total_deduction': queryset.aggregate(sum=Sum('deduction')),
                'total_outstanding': queryset.aggregate(sum=Sum('outstanding')),
                # 'total_salary': queryset.aggregate(sum=Sum('salary')),
                # 'total_tax': queryset.aggregate(sum=Sum('tax')),
            }
            pdf = render_to_pdf(self.template_name, context)
            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'filename="payroll-{period}.pdf"'
                return response
        return HttpResponse(f"""<div style=padding:20;><h1>Payroll period {period} do not exist</h1>
<p>Either the period is not in database or the period is yet to be generated
<p><a href='/home/'>Return Home</a></p></div>""")


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'pdf/pdf_staff_list.html'
    queryset = Employee.active.all()

    def get(self, request, *args, **kwargs):
        context = {
            'employees': self.get_queryset().order_by('id'),
            'num_male': Employee.active.filter(staff__gender='MALE'),
            'num_female': Employee.active.filter(staff__gender='FEMALE'),
            'num_single': Employee.active.filter(staff__marital_status='SINGLE'),
            'num_married': Employee.active.filter(staff__marital_status='MARRIED'),
            'num_management': Employee.active.filter(is_management=True),
            'num_non_management': Employee.active.filter(is_management=False),
        }
        return render_to_pdf(self.template_name, context_dict=context)


class ApplicantListView(LoginRequiredMixin, ListView):
    model = Applicant
    template_name = 'pdf/pdf_apply_list.html'

    def get(self, request, *args, **kwargs):
        context = {
            'applicants': self.get_queryset().order_by('last_name')
        }
        return render_to_pdf(self.template_name, context_dict=context)


class RejectedApplicantList(ListView):
    model = Applicant
    template_name = 'pdf/pdf_apply_rejected_list.html'
    # context_object_name = 'applicants'

    def get(self, request, *args, **kwargs):
        context = {
            'applicants': self.get_queryset().filter(status=False).order_by('last_name')
        }
        return render_to_pdf(self.template_name, context_dict=context)


class PoliciesDocView(LoginRequiredMixin, View):

    template_name = 'pdf/procedures.html'

    def get(self, request, *args, **kwargs):
        context = {

        }
        return render_to_pdf(self.template_name, context_dict=context)


class PayslipView(LoginRequiredMixin, TemplateView):
    template_name = 'pdf/pdf_payslip.html'

    def get(self, request, *args, **kwargs):
        user_input = request.GET['payCode']
        try:
            user_input_list = user_input.split('-')
            period = user_input_list[1] + '-' + user_input_list[2]
            code = int(user_input_list[0])
            staff_id = Employee.active.get(pk=code).id
            person = Payroll.objects.filter(period=period).get(staff_id=staff_id)
            year, month = int(user_input_list[1]), int(user_input_list[2])
            date = datetime.date(year, month, 1)
            month = date.strftime('%B')

            context = {
                'title': 'Payslip',
                'period_month': f"{month}, {year}",
                'paycode': request.GET['payCode'],
                'person': person,
            }
            pdf = render_to_pdf(self.template_name, context)
            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'filename="payslip-{user_input}.pdf"'
                return response
            return HttpResponse(f"""<div style=padding:20;><h1>Payslip {user_input} do not exist</h1>
<p><a href='/home/'>Return Home</a></p></div>""")
        except:
            return HttpResponse(
                """<div style="padding:20;">
                <h2 style="color:red;">Incorrect user input</h2>
                <ul><li>Either the pay code do not exist</li>
                <li>or the user input is entered incorrectly</li>
                <li>Kindly return and check your input</li>
                </ul>
                <a href="/home/">Home</a>
                </div>"""
            )


class StockViewList(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'pdf/pdf_stock_list.html'

    def get(self, request, *args, **kwargs):
        context = {
            'stocks': self.get_queryset().order_by('-pk')
        }
        pdf = render_to_pdf(self.template_name, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'filename="products.pdf"'
            return response
        return HttpResponse("""No such file
        <a href="/home/">Home</a>""")
