import os
import csv
import calendar
import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic.base import TemplateView
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.views.generic import (
                            View, 
                            ListView,
                            DetailView, 
                            CreateView, 
                            UpdateView, 
                            DeleteView
                        )
from .forms import FormProduct
from pdf.utils import render_to_pdf
from pdf.views import Ozone
from .models import (Product, ProductPerformance, ProductExtension)
from .forms import ProductExtensionUpdateForm
from core.models import JsonDataset
from delivery.models import DeliveryNote
from django.db.models import Sum, F, Avg
from ozone import mytools
from core.utils import string_float


permitted_group_name = 'Sales'

def get_date():
    dic = JsonDataset.objects.get(pk=2).dataset
    date_string = dic['closing-stock-date'][0]
    return datetime.datetime.strptime(date_string, '%Y-%m-%d')

    
class ProductHomeView(LoginRequiredMixin, View):

    @staticmethod
    def delivery_qty_values(obj):
        qty_delivered, qty_rejected, amount, amount_credit = list(), list(), list(), list()
        (total_delivered,
         total_rejected,
         percent_rejected,
         total_amount,
         total_amount_credit,
         percent_credited) = 0, 0, '', 0, 0, ''
        for each_record in obj:
            if 'totals' in each_record.products:
                delivered = int(each_record.products['totals']['total_delivered'].replace(',', ''))
                qty_delivered.append(delivered)
                qty_rejected.append(delivered - int(each_record.products['totals']['total_received'].replace(',', '')))

                # values
                value = each_record.products['totals']['total_amount'].replace(',', '')
                value = value.replace(chr(8358), '')
                value_credit = each_record.products['totals']['total_amount_credit'].replace(',', '')
                value_credit = value_credit.replace(chr(8358), '')

                amount.append(float(value))
                amount_credit.append(float(value_credit))

            total_delivered = sum(qty_delivered)
            total_rejected = sum(qty_rejected)
            percent_rejected = f'{100 * total_rejected / total_delivered:,.2f}%'
            total_amount = sum(amount)
            total_amount_credit = sum(amount_credit)
            percent_credited = f"{100 * total_amount_credit / total_amount:,.2f}%"
        return total_delivered, total_rejected, percent_rejected, total_amount, total_amount_credit, percent_credited

    @staticmethod
    def category():
        data_malt = list()
        data_lager = list()
        data_rtd = list()
        data_soft = list()
        data_stout = list()
        data_ed = list()
        data_bitters = list()
        data_na_wine = list()
        data_wine = list()
        data_others = list()
        for each_record in DeliveryNote.objects.all():
            for i in range(1, 4):
                if f'row_{i}' in each_record.products:
                    code = each_record.products[f'row_{i}']['code']
                    category = Product.objects.get(id=int(code)).category
                    if category == 'Malt':
                        data_malt.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'Lager':
                        data_lager.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'RTD':
                        data_rtd.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'Soft':
                        data_soft.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'Stout':
                        data_soft.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'NA Wine':
                        data_na_wine.append(each_record.products[f'row_{i}']['delivered'])
                    elif category == 'Wine':
                        data_wine.append(each_record.products[f'row_{i}']['delivered'])
                    else:
                        data_others.append(each_record.products[f'row_{i}']['delivered'])

        return (sum(data_malt),
                sum(data_lager),
                sum(data_rtd),
                sum(data_soft),
                sum(data_stout),
                sum(data_ed),
                sum(data_bitters),
                sum(data_wine),
                sum(data_na_wine),
                sum(data_others))

    def get(self, request):
        json_data = JsonDataset.objects.get(pk=1).dataset
        
        context = {
            'total_count': Product.objects.all().count(),
            'nb_count': Product.objects.filter(source='NB').count(),
            'gn_count': Product.objects.filter(source='GN').count(),
            'mss_count': Product.objects.filter(source='MSS').count(),
            'ips_count': Product.objects.filter(source='IPS').count(),
            'ib_count': Product.objects.filter(source='IB').count(),
            'quantity_delivered': self.delivery_qty_values(DeliveryNote.objects.all())[0],
            'quantity_rejected': self.delivery_qty_values(DeliveryNote.objects.all())[1],
            'percent_rejected': self.delivery_qty_values(DeliveryNote.objects.all())[2],
            'total_amount': f"{chr(8358)}{self.delivery_qty_values(DeliveryNote.objects.all())[3]:,.2f}",
            'total_amount_credit': f"{chr(8358)}{self.delivery_qty_values(DeliveryNote.objects.all())[4]:,.2f}",
            'percent_credited': self.delivery_qty_values(DeliveryNote.objects.all())[5],
            'total_malt_delivered': self.category()[0],
            'total_lager_delivered': self.category()[1],
            'total_rtd_delivered': self.category()[2],
            'total_soft_delivered': self.category()[3],
            'total_stout_delivered': self.category()[4],
            'total_ed_delivered': self.category()[5],
            'total_bitters_delivered': self.category()[6],
            'total_wine_delivered': self.category()[7],
            'total_na_wine_delivered': self.category()[8],
            'total_others_delivered': self.category()[9],
            'nb_delivered': self.delivery_qty_values(DeliveryNote.objects.filter(source='NB'))[0],
            'nb_amount': f"{chr(8358)}{self.delivery_qty_values(DeliveryNote.objects.filter(source='NB'))[3]:,.2f}",
            'gn_delivered': self.delivery_qty_values(DeliveryNote.objects.filter(source='GN'))[0],
            'gn_amount': f"{chr(8358)}{self.delivery_qty_values(DeliveryNote.objects.filter(source='GN'))[3]:,.2f}",
            'ib_delivered': self.delivery_qty_values(DeliveryNote.objects.filter(source='IB'))[0],
            'ib_amount': f"{chr(8358)}{self.delivery_qty_values(DeliveryNote.objects.filter(source='IB'))[3]:,.2f}",
            'sources': json_data['product-source']     
        }
        return render(request, 'stock/product_home.html', context=context)

class ReportHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'stock/report/home.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with open('stock/text/stock_valued.txt', 'r') as rf:
            content = rf.read()
        if content == 'complete':
            Product.objects.all().update(is_stock_valued=False)
       
        context['is_product_extension'] = ProductExtension.objects.exists()

        content_dict = JsonDataset.objects.get(pk=1).dataset
        context['sources'] = content_dict['product-source']

        obj = JsonDataset.objects.get(pk=2)
        date_string = obj.dataset['closing-stock-date'][0]
        
        context['msg'] = 'Report Based On Fixed Date'
        if self.request.GET != {}:
            if 'theDate' in self.request.GET.keys():
                content = obj.dataset
                content['closing-stock-date'] = [self.request.GET['theDate']]
                obj.dataset = content
                obj.save()
                date_string = obj.dataset['closing-stock-date'][0]
                
            if 'reportDate' in self.request.GET.keys():
                date_string = self.request.GET['reportDate']
                context['msg'] = 'Report Based On Selected Date'

        
        # context['current_date'] = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        context['current_date'] = self.request.user.profile.stock_report_date
        source_list, total_list, sources = list(), list(), list()
        for source in context['sources']:
            qs = ProductExtension.objects.filter(date=context['current_date'], product__source=source)
            qs = qs.annotate(value=F('stock_value')*F('cost_price'))
            source_list.append(qs.order_by('-value'))
            total_list.append(
                (qs.aggregate(Sum('stock_value'))['stock_value__sum'],
                qs.aggregate(Sum('value'))['value__sum'],
                qs.aggregate(Sum('sell_out'))['sell_out__sum'])
            )
            sources.append((
                    {'source': source,
                    'qty': qs.aggregate(Sum('stock_value'))['stock_value__sum'],
                    'value': qs.aggregate(Sum('value'))['value__sum'],
                    'percent': '%',
                    'sellout': qs.aggregate(Sum('sell_out'))['sell_out__sum']
                    }
                    ))

        lis = [i for i in source_list if i.exists()]
        context['obj'] = lis
        total_list = [i for i in total_list if i[0] is not None and i[2] is not None]
        context['totals'] = total_list
        lis = [i for i in sources if i['qty'] is not None and i['sellout'] is not None]
        context['source_total'] = sorted(lis, key=lambda i: i['value'], reverse=True)
        qty, val, sellout = 0, Decimal('0'), 0
        for x, y, z in total_list:
            qty += x
            val += y
            sellout += z

        context['grand_total'] = (qty, val, sellout)
        context['months'] = (calendar.month_name[x] for x in range(1, 13))
        return context
    
    def get(self, request, *args, **kwargs):
        if 'reportDate' in request.GET.keys():
            report_date = datetime.datetime.strptime(request.GET['reportDate'], "%Y-%m-%d").date()
            request.user.profile.stock_report_date = report_date
            request.user.save()
            
        if 'reportPDF' in request.GET.keys():
            if self.request.GET['reportPDF'] == 'on':
                context = self.get_context_data(**kwargs)
                context['logo_image'] = Ozone.logo()
                context['title'] = 'Daily Stock'
                # get template in pdf view
                pdf = render_to_pdf('pdf/pdf_stock_report.html', context_dict=context)
        
                if pdf:
                    response = HttpResponse(pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'filename="dailystock.pdf"'
                    return response
                return HttpResponse('Error')
        return super().get(request, *args, **kwargs)

class ReportStockCategory(LoginRequiredMixin, ListView):
    model = Product
    ordering = 'name'

    def get_queryset(self):
        if self.kwargs['source'] == 'All':
            return super().get_queryset()
        return super().get_queryset().filter(source=self.kwargs['source'])

class ProductDetailedView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Product

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        the_date = JsonDataset.objects.get(pk=2).dataset['closing-stock-date'][0]
        context['theDate'] = datetime.datetime.strptime(the_date, "%Y-%m-%d").date()
        
        product = Product.objects.get(pk=self.kwargs['pk'])
        qs = ProductExtension.objects.filter(product=product).filter(date=context['theDate'])
        
        if qs.exists():
            obj_ext = qs.first()
            context['obj_ext'] = obj_ext
        
        context['is_qs'] = qs.exists()
        return context

    def post(self, request, **kwargs):
        obj = get_object_or_404(Product, pk=self.kwargs['pk'])
        content_dict = JsonDataset.objects.get(pk=2).dataset
        date_string = content_dict['closing-stock-date'][0]
        date_object = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        if 'quantity' in request.POST:
            quantity = request.POST['quantity']    
            ProductExtension.objects.create(
                product=obj,
                stock_value=quantity,
                date=date_object,
                cost_price=obj.cost_price,
                selling_price=obj.unit_price
                )
        else:
            qs = ProductExtension.objects.filter(product=obj).filter(date=date_object)
            if qs.exists():
                stock_obj = qs.first()
                stock_obj.stock_value = request.POST['edit_quantity']
                stock_obj.cost_price = obj.cost_price
                stock_obj.selling_price = obj.unit_price
                stock_obj.save()
            else:
                messages.info(request, "This product's stock does not exist")
        return redirect(obj)

class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'stock/product_form.html'
    form_class = FormProduct
    
    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New'
        return context

class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = FormProduct
    template_name = 'stock/product_form.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Product
    success_url = '/products/list/'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

class PricePageView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'stock/prices.html'

class PriceUpdate(LoginRequiredMixin, UpdateView):
    model = Product

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=kwargs['pk'])
        
        if 'redirect' not in request.POST:
            # selling price gotten from modal form for selling price update only
            if "selling" in request.POST:
                product.unit_price = request.POST['selling']
                product.date_modified = timezone.now()
                msg = f'{product} selling price is updated !!!'
            elif "cost" in request.POST:
                # Cost price gotten from modal form for cost price update only
                product.cost_price = request.POST['cost']
                msg = f'{product} cost price is updated !!!'
            product.save()
        else:        
            json_data = JsonDataset.objects.get(pk=2).dataset
            date_string = json_data['closing-stock-date'][0]
            date_obj = datetime.datetime.strptime(date_string, "%Y-%m-%d")
            qs = ProductExtension.objects.filter(product=product).filter(date=date_obj)
            
            if qs.exists():
                stock_obj = qs.first()
                if "selling" in request.POST:
                    stock_obj.selling_price = request.POST['selling']
                    msg = f'{stock_obj.product} selling price updated !!!'
                elif 'cost' in request.POST:
                    stock_obj.cost_price = request.POST['cost']
                    msg = f'{stock_obj.product} cost price updated !!!'
                stock_obj.save()
                messages.info(request, msg)
            
            return redirect('stock-report-update', source=request.POST['redirect'])    
            
        messages.info(request, msg)
        return redirect(product)
       
class ProductPerformanceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ProductPerformance
    template_name = 'stock/performance/product_list.html'
    ordering = ('-date', 'outlet')

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_queryset(self):
        return super().get_queryset().filter(tag=True)

class ProductPerformanceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProductPerformance
    fields = ('product', 'outlet', 'landing_cost', 'selling_price', 'depletion', 'balance')
    template_name = 'stock/performance/product_form.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New'
        return context

class ProductPerformanceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    fields = ('product', 'outlet', 'landing_cost', 'selling_price', 'depletion', 'balance')
    template_name = 'stock/performance/product_form.html'

    
    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

class ProductPerformanceDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = ProductPerformance
    template_name = 'stock/performance/product_detail.html'


    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

class ProductExtensionUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductExtension
    form_class = ProductExtensionUpdateForm
    template_name = 'stock/report/productextension_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context

    def form_valid(self, form):
        product = ProductExtension.objects.get(pk=self.kwargs['pk'])
        form.instance.selling_price = product.product.unit_price
        return super().form_valid(form)

class ProductExtensionDetailView(LoginRequiredMixin, DetailView):
    model = ProductExtension
    template_name = 'stock/report/productextension_detail.html'

class ProductExtensionListView(LoginRequiredMixin, ListView):
    model = ProductExtension
    template_name = 'stock/report/productextension_monthly.html'

    def get_queryset(self):
        year = datetime.date.today().year
        qs = super().get_queryset().filter(date__year=year)
        qs = qs.annotate(value=F('cost_price')*F('stock_value'))
        
        if self.kwargs['month'] != year:
            return qs.filter(date__month=mytools.Month.month_int(self.kwargs['month']))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_dict = JsonDataset.objects.get(pk=1).dataset
        dataset = list()
        for source in content_dict['product-source']:
            data = list()
            qs = self.get_queryset().filter(product__source=source)
            
            year = datetime.date.today().year
            month = mytools.Month.month_int(self.kwargs['month'])
            for day in range(1, calendar.monthrange(year, month)[1]): 
                date = datetime.date(year, month, day)
                obj = qs.filter(date=date)
                if obj.exists():
                    data.append(
                        {
                        'date': date, 'source': source, 'objs': {
                            'count': f'({obj.count()} of {Product.objects.filter(source=source).count()})',
                            'qty': obj.aggregate(Sum('stock_value'))['stock_value__sum'],
                            'value': obj.aggregate(Sum('value'))['value__sum'],
                            'sellout':obj.aggregate(Sum('sell_out'))['sell_out__sum']
                            }
                        }
                                )
            dataset.append(data)        
        context['dataset'] = dataset
        
        return context
    
class ProductExtensionProduct(LoginRequiredMixin, ListView):
    model = ProductExtension
    template_name = 'stock/report/productextension_productlist.html' 

    def get_queryset(self):
        qs = super().get_queryset().annotate(value=F('cost_price')*F('stock_value'))
        return qs.filter(
            product__source=self.kwargs['source'],
            date__month=mytools.Month.month_int(self.kwargs['month'])
            )     


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = list()
        list_of_products = self.get_queryset().values_list('product__pk', flat=True).distinct()
        for product in list_of_products:
            qs = self.get_queryset().filter(product__pk=product).order_by('date')
            if qs.exists():
                products.append(qs)
        context['products'] = products
        return context

class WatchlistHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'stock/watchlist/home.html'

    def get(self, request, *args, **kwargs):        
        if request.GET != {}:
            for key, value in request.GET.items():
                product = Product.objects.get(pk=key.replace(',', ''))
                # if product.watchlist is true make false and vice versa
                product.watchlist = True if product.watchlist == False else False
                product.save()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_ids = Product.objects.filter(active=True, watchlist=True).values_list('pk', flat=True)
        
        context['products'] = list( ProductExtension.objects.filter(product__pk=ids).latest('date') for ids in product_ids )
        context['date'] = context['products'][0].date
        return context

class WatchlistUpdateView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'stock/watchlist/update.html'
    ordering = 'name'

    def get_queryset(self):
        return super().get_queryset().filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs['action'] == 'add':
            context['products'] = self.get_queryset().filter(watchlist=False)
        elif self.kwargs['action'] == 'remove':
            context['products'] = self.get_queryset().filter(watchlist=True)
        return context

    def get(self, request, *args, **kwargs):
        
        return super().get(request, *args, **kwargs)

class StockReportUpdateView(LoginRequiredMixin, ListView):
    model = ProductExtension
    template_name = 'stock/report/update.html'
    
    def get_queryset(self):
        return super().get_queryset().filter(active=True, date=get_date()).filter(product__source=self.kwargs['source'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date'] = get_date()

        if not self.get_queryset().exists():
            context['message'] = f"Report for this date ({get_date().date().strftime('%d-%b-%Y')}) do not exist !!!"
            context['products'] = Product.objects.filter(active=True, source=self.kwargs['source'])
        return context

    def get(self, request, *args, **kwargs):
        
        if request.GET != {}:
            # convert the request.GET data into a python list of dictionaries
            content_dic = eval(str(request.GET).split('<QueryDict:')[1][:-1])
            
            for key, value in content_dic.items():
                try:
                    product = ProductExtension.objects.get(pk=key.replace(',', ''))
                    product.sell_out = int(value[0].replace(',', ''))
                    product.stock_value = int(value[1].replace(',', ''))
                    product.save()
                    msg = f"Sellout for {kwargs['source']} product(s) added successfully"
                except Exception as err:
                    messages.info(request, f"Records not updated due to {err}. Previous records reloaded")
                    return super().get(request, *args, **kwargs)
            messages.info(request, msg)
            return redirect('stock-report')

        return super().get(request, *args, **kwargs)

class StockReportAddView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'stock/report/add.html'  

    def get_queryset(self):
        return super().get_queryset().filter(active=True).filter(source=self.kwargs['source'])


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date'] = get_date()

        if ProductExtension.objects.filter(active=True, date=get_date(), product__source=self.kwargs['source']).exists():
            context['message'] = "Records for this group already exist"
        return context

    def get(self, request, *args, **kwargs):
        
        if request.GET != {}:
            # convert the request.GET data into a python list of dictionaries
            content_dic = eval(str(request.GET).split('<QueryDict:')[1][:-1])
            i = 0
            for key, value in content_dic.items():
                i += 1
                try:
                    code = key.replace(',', '')
                    obj = self.get_queryset().get(pk=code)
                    ProductExtension.objects.create(
                        product=obj,
                        cost_price=obj.cost_price,
                        selling_price=obj.unit_price,
                        stock_value=value[1].replace(',', ''),
                        date=get_date(),
                        sell_out=value[0].replace(',', ''),
                    )
                    msg = f'{i} Stock Report Generated SUCCESSFULLY !!!'
                except Exception as err:
                    msg = f'Stock Report generation interrupted due to {err}'
                
            messages.info(request, msg)
            return redirect('stock-report')
        return super().get(request, *args, **kwargs)

class StockReportAllProducts(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'stock/report/products.html'
    ordering = 'name'
    paginate_by = 9

class StockReportOneProducts(LoginRequiredMixin, TemplateView):
    template_name = 'stock/report/one_product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = Product.objects.get(pk=kwargs['pk'])
        product = ProductExtension.objects.filter(product=code, date__year=datetime.date.today().year)
        context['product'] = product
        context['sellout'] = product.aggregate(Sum('sell_out'))['sell_out__sum']
        context['daily_average_sellout'] = product.aggregate(Avg('sell_out'))['sell_out__avg']
        context['dataset'] = list(
            {
                'month': datetime.date.strftime(date, '%B'),
                'sellout': product.filter(date__month=date.month).aggregate(Sum('sell_out'))['sell_out__sum'],
                'average': product.filter(date__month=date.month).aggregate(Avg('sell_out'))['sell_out__avg'],
            } for date in product.dates('date', 'month'))
        
        return context

class StockReportHome(LoginRequiredMixin, TemplateView):
    template_name = 'stock/packs/home.html'
    
    def get_context_data(self, **kwargs):
        reports = ProductExtension.objects.filter(date=self.request.user.profile.stock_report_date)
        created = reports.values_list('product__id', flat=True)
        
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['product_report'] = reports
        context['sellout_total'] = reports.aggregate(Sum('sell_out'))['sell_out__sum']
        context['stock_value_total'] = reports.aggregate(Sum('stock_value'))['stock_value__sum']
        sources = Product.objects.filter(active=True).values_list('source', flat=True).distinct()
        querysets = list((source, Product.objects.filter(active=True, source=source)) for source in sources)
        context['querysets'] = querysets
        context['existing_id'] = created
        return context

    def post(self, request, **kwargs):
        
        if request.FILES:
            myfile = request.FILES['fileName']
            # os.path.join(settings.STATIC_ROOT, 'stock')
            dirname = os.path.dirname(__file__)
            fs = FileSystemStorage(location=os.path.join(dirname, 'status'))
            
            for file in os.listdir(fs.location):
                path = os.path.join(fs.location, file)
                if os.path.exists(path):
                    os.remove(path)
            
            filename = fs.save(myfile.name, myfile)
            messages.info(request, f'{filename} uploaded successfully')
        else:
            date = request.POST['date']
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')

            user = User.objects.get(username=kwargs['user'])
            user.profile.stock_report_date = date_obj.date()
            user.save()
            messages.info(request, f'Date has been set to {date_obj.strftime("%d-%b-%Y")} successfully !!!')
            
        return super().get(request, **kwargs)

class BulkUpdateStock(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get(self, request, **kwargs):
        dirname = os.path.join(os.path.dirname(__file__), 'status')
        filename = os.listdir(dirname)[0]
        filepath = os.path.join(dirname, filename)

        context, msg = dict(), list()
        with open(filepath, 'r') as rf:
            content = csv.reader(rf)
            headings = [next(content), next(content), next(content), next(content), next(content)]
            qualifier = [True if len(headings[0]) == 7 else False]
            if qualifier[0] is False:
                msg.append('Number of columns must be seven')
            qualifier.append(headings[2][0].split()[1] == headings[2][0].split()[3])
            if qualifier[1] is False:
                msg.append("File's date is missing or date is more than one day")
            qualifier.append(headings[3][0] == 'All Items' and headings[3][1] == 'All MC')
            if qualifier[2] is False:
                msg.append("File may not have taken all items or all MCs")
            qualifier.append(all(headings[-1]) and headings[-1][-1]=='Cost Price' and headings[-1][0]=='Product code')
            if qualifier[3] is False:
                msg.append("File columns may differ from what is expected")

            if all(qualifier):
                date_string = headings[2][0].split()[1]
                date_obj = datetime.date(int(date_string.split('-')[2]), int(date_string.split('-')[1]), int(date_string.split('-')[0]))
                
                try:
                    dataset = [{
                        'id': int(record[0]),
                        'product': Product.objects.get(pk=int(record[0])) if Product.objects.filter(pk=int(record[0])).exists() else 'Product not found',
                        'item': record[1],
                        'sellout': int(string_float(record[2])),
                        'selling_price': string_float(record[3]),
                        'sales_amount': string_float(record[4]),
                        'closing_balance': int(string_float(record[5])),
                        'cost_price': string_float(record[6])
                    } for record in content if record[0] != '']  
                    
                    context = {
                        'date': date_obj,
                        'filename': filepath,
                        "dataset": dataset,
                    }
                    
                    post_dataset = list()
                    lock_save = False
                    for data in dataset:
                        X = data.copy()
                        product = X.pop('product')
                        del X['item']
                        try:
                            product.id
                        except:
                            messages.warning(request, "This dataset is not fit to go into database !!!")
                            lock_save = True
                            break
                        else:
                            X.update({'id': product.id})
                            post_dataset.append(X)
                    context['post_dataset'] = post_dataset
                except:
                    messages.warning(request, "CSV not well prepared for the database")
                    lock_save = True
        context['lock_save'] = lock_save
        context['qualifier'] = all(qualifier) #boolean 
        context['msg'] = msg #list
        return render(request, 'stock/packs/bulk_update.html', context=context)
        

    def post(self, request, **kwargs):
        # fetch from post request the date and the list of data for update to the model
        date = datetime.datetime.strptime(request.POST['date'], '%B %d, %Y').date()
        content = request.POST['content']
        list_data = eval(content)

        #note: check the record dictionary for adequacy
        for record in list_data:
            try:
                obj, created = ProductExtension.objects.update_or_create(
                    product_id=record['id'],
                    date=date,
                    defaults={
                        'cost_price': record['cost_price'],
                        'selling_price': record['selling_price'],
                        'stock_value': record['closing_balance'],
                        'sell_out': record['sellout'],
                        'sales_amount': record['sales_amount'],
                    }
                )
            except:
                messages.warning(request, f"{obj} failed to join database!!!. Process is hereby aborted")
                return self.get(request, **kwargs)
        messages.success(request, f"All records updated or saved into database !!!")
        return self.get(request, **kwargs)

class StockReportNew(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProductExtension
    template_name = 'stock/report/productextension_form.html'
    fields = ['sell_out', 'stock_value', 'sales_amount']

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = Product.objects.get(pk=self.kwargs['pk'])
        context['product'] = product
        context['date'] = datetime.datetime.strptime(self.kwargs['date'], '%Y-%m-%d').date()
        return context

    def get(self, request, *args, **kwargs):
        date_obj = datetime.datetime.strptime(kwargs['date'], '%Y-%m-%d').date()
        product = Product.objects.get(pk=kwargs['pk'])
        qs = self.get_queryset().filter(product=product, date=date_obj)
        if qs.exists():
            messages.info(request, f'{product} already ADDED, you can only UPDATE')
            return redirect('stock-report-home', user=request.user)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        product = Product.objects.get(id=self.kwargs['pk'])
        form.instance.product_id = product.pk
        form.instance.cost_price = product.cost_price
        form.instance.selling_price = product.unit_price
        form.instance.date = datetime.datetime.strptime(self.kwargs['date'], '%Y-%m-%d').date()

        return super().form_valid(form)

class StockReportUpdate(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        product = Product.objects.get(pk=kwargs['code'])
        date_obj = datetime.datetime.strptime(self.kwargs['date'], '%Y-%m-%d').date()
        qs = ProductExtension.objects.filter(product=product, date=date_obj)
        if not qs.exists():
            messages.info(request, f'{product} not ADDED, Please add before you can UPDATE')
            return redirect('stock-report-home', user=request.user)
        bound_form = ProductExtensionUpdateForm(instance=qs.get())
        
        context = {
            'product': product,
            'date': date_obj,
            'form': bound_form
        }
        return render(request, 'stock/packs/update.html', context)

    def post(self, request, **kwargs):
        product = Product.objects.get(pk=kwargs['code'])
        date_obj = datetime.datetime.strptime(self.kwargs['date'], '%Y-%m-%d').date()
        qs = ProductExtension.objects.filter(product=product, date=date_obj)
        obj = get_object_or_404(qs)
        bound_form = ProductExtensionUpdateForm(request.POST, instance=obj)
        if bound_form.is_valid():
            bound_form.save()
        return redirect('stock-report-home', user=request.user)

class StockReportDetail(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'stock/report/productextension_detail.html'
    
    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = Product.objects.get(pk=self.kwargs['code'])
        date_obj = datetime.datetime.strptime(self.kwargs['date'], '%Y-%m-%d').date()
        context['object'] = ProductExtension.objects.filter(product=product, date=date_obj).get()
        return context

class ProductStatusUpdate(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def post(self, request, **kwargs):
        product = get_object_or_404(Product, pk=kwargs['pk'])
        product.active = False if product.active is True else True  
        product.save() 
        return redirect(product)

class PerformanceHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'stock/performance/home.html'
    
    def color(self, indicator):
        if indicator < 50:
            x = ('text-danger', 'Poor')
        elif 50 <= indicator < 70:
            x = ('text-warning', 'Fair')
        elif 70 <= indicator < 90:
            x = ('text-primary', 'Good')
        else:
            x = ('text-success', 'Excellent')
        return x

    def month_process(self, qs, qs_month):
        dates = qs.values_list('date', flat=True).distinct()
        number_of_dates = dates.count()
        products = qs.values_list('product', flat=True).distinct()
        product_list = []
        for product in products:
            N = 0
            for date in dates:
                obj = qs_month.filter(product=product).filter(date=date)
                
                if obj.exists():
                    N += 1
            if number_of_dates == N:
                product_list.append(obj.get()) 
        return product_list  # a list of object 
            
    def product_analyzer(self, ops, field, field_type, qs):
        """
            This function is to give a tuple of the product object and the sum
            or average of a field in the ProductExtension model
        """
        products = Product.objects.all()
        str_ops = 'sum' if ops == Sum else 'avg'
        sell_out_list = [
                (product, qs.filter(product=product).aggregate(ops(field))[f'{field}__{str_ops}']) 
            for product in products
        ]

        value, product_data = field_type(), tuple()

        # Go through the list to remove the None type
        for sellout in sell_out_list:
            if not isinstance(sellout[1], field_type):
                continue
        
            if sellout[1] > value:
                value = sellout[1]

            product_data = sellout
        
        return product_data #max(sell_out_list, key=lambda X:X[1])
                
    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        #Most Sellout - YTD
        dataset = ProductExtension.objects.all()
        context['record_exist'] = True if dataset.exists() else False
  
        if dataset.exists():
            latest_record = dataset.latest('date')
            qs = dataset.filter(date__year=latest_record.date.year)
            qs_month = qs.filter(date__month=latest_record.date.month)
            
            qs_day = dataset.filter(date=latest_record.date) #qs.filter(date__day=latest_record.date.day)
            qs_day = qs_day.annotate(value=F('cost_price')*F('stock_value'))
            qs_day = qs_day.annotate(profit=F('sell_out')*(F('selling_price')-F('cost_price')))
            
            context['sales'] = qs_day.filter(sell_out__gt=0)
            context['products'] = Product.objects.filter(active=True)
            context['inactive_products'] = Product.objects.filter(active=False)
            context['sales_amount_total'] = qs_day.aggregate(Sum('sales_amount'))['sales_amount__sum']
            context['sellout_total'] = qs_day.aggregate(Sum('sell_out'))['sell_out__sum']
            context['stock_value_total'] = qs_day.aggregate(Sum('value'))['value__sum']
            context['profit_total'] = qs_day.aggregate(Sum('profit'))['profit__sum']

            """In the ProductExtension model, products without stock and sellout are not created even though
            the product may be active. For this reason, we exploit the models to extract the/those product(s)
            as follows
            """
            products_1 = Product.objects.filter(active=True).values_list('pk', flat=True)
            products_2 = qs_day.values_list('product', flat=True).distinct()
            products = products_1.difference(products_2)
            products = products.union(qs_day.filter(stock_value__lte=0).values_list('product', flat=True))

            context['no_stock'] = Product.objects.filter(pk__in=products)
            
            context['low_stock'] = qs_day.filter(stock_value__lt=10).exclude(stock_value__lte=0)
            context['no_sellout'] = qs_day.filter(stock_value__gt=0).filter(sell_out=0)
            context['low_sellout'] = qs_day.filter(sell_out__lt=10).exclude(sell_out=0)

            context['no_stock_month'] = self.month_process(qs_month, qs_month.filter(stock_value__lte=0))
            context['low_stock_month'] = self.month_process(qs_month, qs_month.filter(stock_value__lt=10).exclude(stock_value__lte=0))
            zero_sellout = self.month_process(qs_month, qs_month.filter(stock_value__gt=0).filter(sell_out=0))
            context['low_sellout_month'] = self.month_process(qs_month, qs_month.filter(sell_out__lt=10).exclude(sell_out=0))

            context['no_sellout_month'] = zero_sellout
            if zero_sellout:
                """Locked down capital is the value in stock that have not sold even ones in the month"""
                total = sum([obj.stock_value * obj.cost_price for obj in zero_sellout])
                context['lcd'] = float(total.amount)

            context['availability_ratio'] = 100 * (1 - context['no_stock'].count()/context['products'].count())
            context['av_color'] = self.color(context['availability_ratio'])
            context['movement_ratio'] = 100 * (1 - context['no_sellout'].count()/(context['products'].count() - context['no_stock'].count()))
            context['mv_color'] = self.color(context['movement_ratio'])
            
        if ProductExtension.objects.exists():
            latest_date = ProductExtension.objects.latest('date').date
            context['current_date'] = latest_date
            product_extension = ProductExtension.objects.filter(sell_out__gt=0).exclude(product__name__icontains='Empty')
            # Most sold out product of the day
            qs_data = product_extension.filter(date=latest_date)
            # get a tuple of the product and the sellout
            data = qs_data.values_list('product', 'sell_out') 
            max_sellout = max(data, key=lambda x:x[1]) # --> (n, n)
            highest_sellout_day = (Product.objects.get(pk=max_sellout[0]).nickname(), max_sellout[1])

            #put date in context
            context['highest_sellout_day'] = highest_sellout_day

            # Most soldout product of the month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month).filter(sell_out__gt=0)
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_sellout_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sell_out'))['sell_out__sum'])
                for product in products
            ]
            max_sellout = max(most_sellout_list, key=lambda x:x[1])
            highest_sellout_month = (Product.objects.get(pk=max_sellout[0]).nickname(), max_sellout[1])
            context['highest_sellout_month'] = highest_sellout_month
            
            """Most soldout product of the year"""
            qs_data = product_extension.filter(date__year=latest_date.year)
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_sellout_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sell_out'))['sell_out__sum'])
                for product in products
            ]
            max_sellout = max(most_sellout_list, key=lambda x:x[1])
            highest_sellout_year = (Product.objects.get(pk=max_sellout[0]).nickname(), max_sellout[1])
            context['highest_sellout_year'] = highest_sellout_year
            
            """This section is for the most profitable"""
            # For the latest date
            qs_data = product_extension.filter(date=latest_date)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))
            
            # get a tuple of the product and the sellout
            data = qs_data.values_list('product', 'profit') 
            
            max_profit = max(data, key=lambda x:x[1]) # --> (n, n)
            highest_profit_day = (Product.objects.get(pk=max_profit[0]).nickname(), max_profit[1])

            context['most_profitable_day'] = highest_profit_day

            # for the latest date's month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('profit'))['profit__sum'])
                for product in products
            ]
            max_profit = max(most_profit_list, key=lambda x:x[1])
            highest_profit_month = (Product.objects.get(pk=max_profit[0]).nickname(), max_profit[1])
            context['most_profitable_month'] = highest_profit_month
            
            # for the latest date's month
            qs_data = product_extension.filter(date__year=latest_date.year)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('profit'))['profit__sum'])
                for product in products
            ]
            max_profit = max(most_profit_list, key=lambda x:x[1])
            highest_profit_year = (Product.objects.get(pk=max_profit[0]).nickname(), max_profit[1])
            context['most_profitable_year'] = highest_profit_year
            
            # Margins
            # 1. the product with the best margin
            qs_data = product_extension.filter(date=latest_date).filter(sell_out__gt=0)
            qs_data = qs_data.annotate(margin=F('selling_price') - F('cost_price'))
            
            # get a tuple of the product and the sellout
            data = qs_data.values_list('product', 'margin') 
        
            max_margin = max(data, key=lambda x:x[1]) # --> (n, n)
            highest_margin_day = (Product.objects.get(pk=max_margin[0]).nickname(), max_margin[1])
            context['best_margin_day'] = highest_margin_day

            #2. the product with the worst margin
            min_margin = min(data, key=lambda x:x[1])
            lowest_margin_day = (Product.objects.get(pk=min_margin[0]).nickname(), min_margin[1])
            context['worst_margin_day'] = lowest_margin_day

            #3 Average margin
            qs_data = qs_data.annotate(profit=F('sell_out') * F('margin'))
            total_profit = qs_data.aggregate(Sum('profit'))['profit__sum']
            total_sales = qs_data.aggregate(Sum('sales_amount'))['sales_amount__sum']
            context['average_margin'] = float(total_profit/total_sales) * 100 
            
            """The gross sales"""
            #1. Product with the highest gross sales value
            qs_data = product_extension.filter(date=latest_date)
            
                # get a tuple of the product and the sales
            data = qs_data.values_list('product', 'sales_amount') 
            
            max_sales = max(data, key=lambda x:x[1]) # --> (n, n)
            highest_sales_day = (Product.objects.get(pk=max_sales[0]).nickname(), float(max_sales[1]))
            context['most_sales_day'] = highest_sales_day

            #2. Product with the highest GSV in the month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month)
            
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sales_amount'))['sales_amount__sum'])
                for product in products
            ]
            max_sales = max(most_profit_list, key=lambda x:x[1])
            highest_sales_month = (Product.objects.get(pk=max_sales[0]).nickname(), float(max_sales[1]))
            context['most_sales_month'] = highest_sales_month
            
            #2. Product with the highest GSV for the year
            qs_data = product_extension.filter(date__year=latest_date.year)
            
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sales_amount'))['sales_amount__sum'])
                for product in products
            ]
            max_sales = max(most_profit_list, key=lambda x:x[1])
            highest_sales_year = (Product.objects.get(pk=max_sales[0]).nickname(), float(max_sales[1]))
            context['most_sales_year'] = highest_sales_year
        return context

class ProductAnalysisView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'stock/product_analysis.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def sort_dict(obj):
        if obj['sellout'] is not None:
            return obj['sellout']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        """Run rate with 3 weeks stock, Top 10 most selling products and its profit
            We will consider least selling  
        """

        all_products_qs = list() # a list that will contain dictionary   

        if Product.objects.exclude(name__icontains='Empty').exists():
            active_products = Product.objects.filter(active=True).values_list('pk', flat=True).distinct().order_by('source')
        else:
            return context

        if ProductExtension.objects.exists():
            date2 = ProductExtension.objects.latest('date').date
            date1 = date2 - datetime.timedelta(days=4) if date2.weekday() == 0 or date2.weekday() == 1 else date2 - datetime.timedelta(days=3)
        else:
            return context

        for product in active_products:
            product_data = ProductExtension.objects.filter(product=product)
            product_data = product_data.annotate(profit=F('sell_out')*(F('selling_price')-F('cost_price')))
            
            if product_data.exists():
                product_data_3days_ago = product_data.filter(date__range=[date1, date2])
                average_sellout = product_data.aggregate(Avg('sell_out'))['sell_out__avg']
                run_rate = 0 if average_sellout is None else int(18*average_sellout)

                sellout = product_data_3days_ago.aggregate(Sum('sell_out'))['sell_out__sum']
                sellout = 0 if sellout is None else sellout

                profit = product_data_3days_ago.aggregate(Sum('profit'))['profit__sum']
                profit = 0 if profit is None else profit

                all_products_qs.append({
                    'name': product_data.first().product, 
                    'run_rate': run_rate,
                    'closing_stock': product_data.last().stock_value,
                    'sellout': sellout, 
                    'profit': profit
                    })      
        
        if all_products_qs: 
            sort_qs_by_sellout = sorted(all_products_qs, key=lambda x:x['sellout'], reverse=True)[:10]
            context['sort_qs_by_sellout'] = sort_qs_by_sellout
        
        context['current_date'] = date1 
        context['all_products_qs'] = all_products_qs
    
        # products that have not sold out in the last 7 days even though they are available        
        no_sellout = list()
        date3 = date2 - datetime.timedelta(days=7)
        product_data_7days_ago = product_data.filter(date__range=[date3, date2]).filter(stock_value__gt=0).filter(sell_out=0)
        
        if product_data_7days_ago.exists():
            sold = ProductExtension.objects.filter(product=product).filter(sell_out__gt=0)
            date = sold.last().date if sold.exists() else datetime.date(1, 1, datetime.date.today().year)

            no_sellout.append(
                {
                    'product': product_data_7days_ago.first().product,
                    'closing_stock': product_data_7days_ago.last().stock_value,
                    'sold': sold.last().sell_out,
                    'date': date
                }
            )            
        context['no_sellout'] = no_sellout 
        
        return context
