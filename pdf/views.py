import datetime
import decimal
import os
import base64
import random
from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import redirect
from pdf.utils import render_to_pdf
from customer.models import CustomerProfile
from apply.models import Applicant
from django.contrib.auth.models import User
from django.views.generic import (View, ListView, DetailView, TemplateView)
from staff.models import Employee, Payroll, EmployeeBalance
from trade.models import TradeMonthly
from stock.models import Product
from brief.models import Post
from django.db.models import Sum, F, Avg, Min, ExpressionWrapper, DecimalField
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.utils import timezone

class Ozone:

    def logo():
        path = os.path.join(settings.BASE_DIR, 'customer/static/customer/logo.png')
        with open(path, 'rb') as rf:
            content = rf.read()
        buf = BytesIO(content)
        logo = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
        buf.close()
        return logo


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
        path = os.path.join(settings.BASE_DIR, 'customer/static/customer/logo.png')
        with open(path, 'rb') as rf:
            content = rf.read()
        buf = BytesIO(content)
        logo = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
        buf.close()
            
        # file = base64.b64encode(content.getvalue()).decode('utf-8').replace('\n', '')
        period = kwargs['period']
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
                'credentials': f"{request.user.first_name} {request.user.last_name}",
                'approval': Employee.active.first(),
                'today': datetime.datetime.now(),
                'period': period,
                'period_month': period_word,
                'employees': queryset.order_by('-staff'),
                'total_net_pay': queryset.aggregate(sum=Sum('net_pay')),
                'total_debit': queryset.aggregate(sum=Sum('debit_amount')),
                'total_credit': queryset.aggregate(sum=Sum('credit_amount')),
                'total_deduction': queryset.aggregate(sum=Sum('deduction')),
                'total_outstanding': queryset.aggregate(sum=Sum('outstanding')),
                'logo_image': logo
            
                # 'total_salary': queryset.aggregate(sum=Sum('salary')),
                # 'total_tax': queryset.aggregate(sum=Sum('tax')),
            }
            pdf = render_to_pdf(self.template_name, context)
            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'filename="payroll-{period}{random.randint(1, 10000)}.pdf"'
                return response
        return HttpResponse(f"""<div style=padding:20;><h1>Payroll period {period} do not exist</h1>
<p>Either the period is not in database or the period is yet to be generated
<p><a href='/home/'>Return Home</a></p></div>""")


class EmployeeListView(LoginRequiredMixin, ListView):
    template_name = 'pdf/pdf_staff_list.html'
    queryset = Employee.active.all()

    def get(self, request, *args, **kwargs):
        context = {
            'employees': self.get_queryset().order_by('id'),
            'num_male': self.get_queryset().filter(staff__gender='MALE'),
            'num_female': Employee.active.filter(staff__gender='FEMALE'),
            'num_single': Employee.active.filter(staff__marital_status='SINGLE'),
            'num_married': Employee.active.filter(staff__marital_status='MARRIED'),
            'num_management': Employee.active.filter(is_management=True),
            'num_non_management': Employee.active.filter(is_management=False),
        }
        return render_to_pdf(self.template_name, context_dict=context)


class EmployeeSummaryView(LoginRequiredMixin, ListView):
    queryset = Employee.active.all()
    template_name = 'pdf/pdf_staff_summary.html'

    def get(self, request, *args, **kwargs):
        grads = self.get_queryset().exclude(
            staff__qualification='NONE').exclude(
            staff__qualification='ND/NCE').exclude(
            staff__qualification='PRIMARY').exclude(
            staff__qualification='SECONDARY')

        annual_salary = self.get_queryset().annotate(total_salary=12*(F('basic_salary') + F('allowance')))
        monthly_salary = self.get_queryset().annotate(total_salary=F('basic_salary') + F('allowance'))
        cr = EmployeeBalance.objects.filter(value_type='Cr').aggregate(total=Sum('value'))['total']
        dr = EmployeeBalance.objects.filter(value_type='Dr').aggregate(total=Sum('value'))['total']
        
        context = {
            'now': datetime.datetime.now(),
            'workforce': self.get_queryset(),
            'num_female': self.get_queryset().filter(staff__gender='FEMALE'),
            'num_male': self.get_queryset().filter(staff__gender='MALE'),
            'num_single': self.get_queryset().filter(staff__marital_status='SINGLE'),
            'num_married': self.get_queryset().filter(staff__marital_status='MARRIED'),
            'num_management': self.get_queryset().filter(is_management=True),
            'num_non_management': self.get_queryset().filter(is_management=False),
            'num_all_time': Employee.objects.count(),
            'num_probation': self.get_queryset().filter(is_confirmed=False),
            'num_graduates': grads,
            'total_salary': annual_salary.aggregate(total=Sum('total_salary'))['total'],
            'balance': cr - dr,
            'average_salary': monthly_salary.aggregate(tsa=Avg('total_salary')),
            'total_net_pay': Payroll.objects.aggregate(total=Sum('net_pay')),
            'minimum_wage': monthly_salary.aggregate(value=Min('total_salary')),
            'youngest': self.get_queryset().latest('staff__birth_date').staff.birth_date,
            'oldest': self.get_queryset().earliest('staff__birth_date').staff.birth_date,
            'sales_last_year': TradeMonthly.objects.filter(year=f'{datetime.date.today().year-1}').aggregate(Sum('sales'))['sales__sum'],
            'sales_year': TradeMonthly.objects.filter(year=f'{datetime.date.today().year}').aggregate(Sum('sales'))['sales__sum'],
        }
        
        context['gross_margin_last_year'] = TradeMonthly.objects.filter(year=f'{datetime.date.today().year-1}').aggregate(Sum('gross_profit'))['gross_profit__sum']
        context['gross_margin_year'] = TradeMonthly.objects.filter(year=f'{datetime.date.today().year}').aggregate(Sum('gross_profit'))['gross_profit__sum']
        if context['sales_last_year'] != None:
            context['gross_margin_last_year'] = 100 * context['gross_margin_last_year']/context['sales_last_year']
        if context['sales_year'] != None:
            context['gross_margin_year'] = 100 * context['gross_margin_year']/context['sales_year']
        
        
        monthly_qs = TradeMonthly.objects.filter(year=str(datetime.date.today().year)).annotate(gp_ratio=ExpressionWrapper(100*F('gross_profit')/F('sales'), output_field=DecimalField()))
        context['xx'] = monthly_qs.aggregate(Sum('gross_profit'))
        return render_to_pdf(template_src=self.template_name, context_dict=context)


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
            
            cr = EmployeeBalance.objects.filter(staff=staff_id, period=period, value_type='Cr').aggregate(Sum('value'))['value__sum']
            dr = EmployeeBalance.objects.filter(staff=staff_id, period=period, value_type='Dr').aggregate(Sum('value'))['value__sum']
            Cr = decimal.Decimal('0') if cr is None else cr
            Dr = decimal.Decimal('0') if dr is None else dr
            
            context = {
                'title': 'Payslip',
                'period_month': f"{month}, {year}",
                'paycode': request.GET['payCode'],
                'person': person,
                'logo_image': Ozone.logo(),
                'gratuity': Cr - Dr
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
                <h2 style="color:red;">Possible Errors</h2>
                <ul><li>Either the pay code do not exist</li>
                <li>Server connection not established, check your internet</li>
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


class PriceChange(LoginRequiredMixin, TemplateView):
    template_name = 'pdf/current_price.html'

    def get(self, request, *args, **kwargs):
        products = Product.objects.filter(active=True)
        products = products.filter(date_modified__date=timezone.now())
        
        try:
            with open('extrafiles/price-update-footnote.txt', 'r') as rf:
                content = rf.read()
        except:
            content = 'Footnote file not found'
        context = {
            'products': products,
            'logo_image': Ozone.logo(),
            'title': 'Recently Updated Prices',
            'price_update_footnote': content
        }
        pdf = render_to_pdf(self.template_name, context_dict=context)
        
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            today = datetime.date.today().strftime('%d%m%Y')
            response['Content-Disposition'] = f'filename="change-price-{today}.pdf"'
            return response
        return HttpResponse('Error')
    

class ProductBySource(LoginRequiredMixin, TemplateView):
    template_name = 'pdf/current_price.html'

    # def footnote():
    #     with open()

    def get(self, request, *args, **kwargs):
        products = Product.objects.filter(active=True)
        if kwargs['source'] == 'Others':
            products = products.exclude(source='NB').exclude(source='GN').exclude(source='IB')
        elif kwargs['source'] == 'All':
            pass
        else:
            products = products.filter(source=kwargs['source'])
        
        if kwargs['source'] == 'NB':
            title = "Nigerian Breweries"
        elif kwargs['source'] == 'GN':
            title = 'Guinness Nigeria Plc'
        elif kwargs['source'] == 'IB':
            title = 'International Breweries'
        elif kwargs['source'] == 'Others':
            title = 'Others'
        else:
            title = 'All'

        context = {
            'products': products,
            'logo_image': Ozone.logo(),
            'title': title 
            
        }
        pdf = render_to_pdf(self.template_name, context_dict=context)
        
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            today = datetime.date.today().strftime('%d%m%Y')
            response['Content-Disposition'] = f'filename="{kwargs.get("source").lower()}-price-{today}.pdf"'
            return response
        return HttpResponse('Error')
    

class TodayPostPdf(LoginRequiredMixin, TemplateView):
    template_name = 'pdf/today_post.html'

    def get(self, request, *args, **kwargs):
        posts = Post.objects.filter(date_created=datetime.date.today())
        context = {
            'posts': posts.order_by('-pk'),
            'logo_image': Ozone.logo()
        }
        pdf = render_to_pdf(self.template_name, context_dict=context)
        
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            today = datetime.date.today().strftime('%d%m%Y')
            response['Content-Disposition'] = f'filename="daily-brief-{today}.pdf"'
            return response
        return HttpResponse('Error')
    

class PriceUpdateFootNote(View):
    def get(self, request, *args, **kwargs):
        content = request.GET['footnote']
        with open('extrafiles/price-update-footnote.txt', 'w') as wf:
            wf.write(content)
        return redirect('product-home')