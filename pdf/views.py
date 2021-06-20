from django.views.generic import (
                                  View,)
import datetime
from django.http import HttpResponse
from pdf.utils import render_to_pdf
from customer.models import CustomerProfile
from apply.models import Applicant
from django.contrib.auth.models import User
from django.views.generic import ListView
from staff.models import Employee
from django.db.models import Sum
from decimal import Decimal
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
    model = Employee
    template_name = 'pdf/pdf_payroll.html'
    context_object_name = 'employees'

    def get(self, request, *args, **kwargs):
        total = [
        self.get_queryset().aggregate(sum=Sum('basic_salary')),
        self.get_queryset().aggregate(sum=Sum('allowance')),
        ]
        X = 0
        for value in total:
            X += value.get('sum')
        total.append({'sum': X})
        total.append(self.get_queryset().aggregate(sum=Sum('tax_amount')))
        total.append({'sum': total[2].get('sum') - total[3].get('sum')})

        """the debit and credit will be from another model"""
        total.append({'sum': Decimal(20000)})
        total.append({'sum': Decimal(24000)})

        total.append({'sum': total[4].get('sum')
                             - total[5].get('sum') + total[6].get('sum')}
                     )

        context = {
            'today': datetime.datetime.now(),
            'host': f"{request.META.get('HTTP_HOST')} | {request.user}",
            'users': User.objects.all(),
            'employees': self.get_queryset().order_by('staff'),
            'totals': total,
        }
        pdf = render_to_pdf(self.template_name, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            return response
        return HttpResponse('Payroll not ready')


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'pdf/pdf_staff_list.html'

    def get(self, request, *args, **kwargs):
        context = {
            'employees': self.get_queryset().order_by('staff')
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
