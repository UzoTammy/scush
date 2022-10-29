import calendar
import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic.base import TemplateView
from django.contrib import messages
from django.contrib.auth.models import Group, User
from pdf.utils import render_to_pdf
from pdf.views import Ozone
from .models import (Product, ProductPerformance, ProductExtension)
from .forms import ProductExtensionUpdateForm
from core.models import JsonDataset
from delivery.models import DeliveryNote
from django.db.models import Sum, F, Avg
from django.views.generic import (
    View, ListView, DetailView, CreateView, UpdateView, DeleteView)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from ozone import mytools


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
    model = Product
    fields = '__all__'

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
    fields = '__all__'

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
        # all_products = Product.objects.filter(active=True).values_list('id', flat=True)
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
        date = request.POST['date']
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')

        user = User.objects.get(username=kwargs['user'])
        user.profile.stock_report_date = date_obj.date()
        user.save()

        messages.info(request, f'Date has been set to {date_obj.strftime("%d-%b-%Y")} successfully !!!')
        return super().get(request, **kwargs)

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

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #Most Sellout
        products = Product.objects.all()
        qs = ProductExtension.objects.filter(date__year=datetime.date.today().year)
        sell_out_list = [(
            product, 
            qs.filter(product=product).aggregate(Sum('sell_out'))['sell_out__sum']) 
            for product in products]
        value, most_sellout = 0, tuple()
        for product in sell_out_list:
            if product[1] == None:
                continue
            if product[1] > value:
                value = product[1]
                most_sellout = product
        context['most_sellout'] = most_sellout

        # Most profitable
        qs = qs.annotate(profit=F('sell_out')*(F('selling_price')-F('cost_price')))
        profit_list = [
            (product,
            qs.filter(product=product).aggregate(Sum('profit'))['profit__sum'])
            for product in products
        ]
        value, most_profitable = Decimal(0), tuple()
        for product in profit_list:
            if not isinstance(product[1], Decimal):
                continue
            if product[1] > value:
                value = product[1]
                most_profitable = product
        context['most_profitable'] = most_profitable
        
        #Most Margin
        qs = qs.annotate(margin=F('selling_price')-F('cost_price'))
        margin_list = [
            (product,
            qs.filter(product=product).aggregate(Avg('margin'))['margin__avg'])
            for product in products
        ]
        value, most_margin = Decimal(0), tuple()
        for product in margin_list:
            if not isinstance(product[1], Decimal):
                continue
            if product[1] > value:
                value = product[1]
                most_margin = product
        context['most_margin'] = most_margin

        #Most Gross Sales
        gross_value_list = [
            (product,
            qs.filter(product=product).aggregate(Sum('sales_amount'))['sales_amount__sum']
            ) for product in products
        ]
        value, most_gross_sales = Decimal(0), tuple()
        for product in gross_value_list:
            if not isinstance(product[1], Decimal):
                continue
            if product[1] > value:
                value = product[1]
                most_gross_sales = product
            context['most_gross_sales'] = most_gross_sales
        return context

