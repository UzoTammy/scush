import datetime
from django.contrib import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.base import TemplateView
from .models import (Product, ProductPerformance, ProductExtension, SOURCES)
from delivery.models import DeliveryNote
from django.views.generic import View
from django.template.loader import get_template
from django.http import HttpResponse
from django.views.generic import (ListView,
                                  DetailView,
                                  CreateView,
                                  UpdateView,
                                  DeleteView)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


permitted_group_name = 'Sales'


class MyFirstView(View):

    def get(self, request):

        context = {
            'products': Product.objects.all(),
        }
        response = get_template('stock/myfirst.html').render(context, request)
        return HttpResponse(response)


class ProductHomeView(View):

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
        with open('stock/text/stock_valued.txt', 'r') as rf:
            content = rf.read()
        if content == 'complete':
            Product.objects.all().update(is_stock_valued=False)
        
        context = {
            'total_count': Product.objects.all().count(),
            'nb_count': Product.objects.filter(source='NB').count(),
            'gn_count': Product.objects.filter(source='GN').count(),
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
            'is_product_extension': ProductExtension.objects.exists()
        }
        return render(request, 'stock/product_home.html', context=context)


class ProductListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Product
    ordering = '-pk'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class ProductTabularCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProductExtension
    template_name = 'stock/product_tabular.html'
    fields = ('stock_value',)
    success_url = reverse_lazy('product-tabular')

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            the_date = datetime.datetime.strptime(self.request.GET.get('theDate'), '%Y-%m-%d').date()
            context['the_date'] = the_date
            with open('stock/text/date.txt', 'w') as wf:
                wf.write(self.request.GET.get('theDate'))
        except Exception as err:
            with open('stock/text/date.txt', 'r') as rf:
                the_date = rf.read()
            the_date = datetime.datetime.strptime(the_date, '%Y-%m-%d').date()    
            context['the_date'] = the_date

        context['products'] = Product.objects.filter(is_stock_valued=False)

        if context['products'].count()==0:
            context['complete'] = True
            with open('stock/text/stock_valued.txt', 'w') as wf:
                wf.write('complete')  
        else:
            context['complete'] = False 
            with open('stock/text/stock_valued.txt', 'w') as wf:
                wf.write('incomplete')
        
        """Check the latest entry"""
        latest_date = ProductExtension.objects.latest('date').date
        qs_count = ProductExtension.objects.filter(date=latest_date).count()
        product_count = Product.objects.count()
        if qs_count != product_count and latest_date != the_date:
            context['product_assesment'] = (latest_date, True, qs_count, product_count)
        return context

    def form_valid(self, form):
        product = get_object_or_404(Product, pk=self.request.POST['pk'])
        form.instance.product = product
        form.instance.cost_price = product.cost_price
        form.instance.selling_price = product.unit_price
        form.instance.date = self.get_context_data(kwargs={}).get('the_date')
        product.is_stock_valued = True
        product.save()
        messages.info(self.request, f'Stock Value for {form.instance.product} added Successfully !!!')
        return super().form_valid(form)


class ProductTabularListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ProductExtension
    template_name = 'stock/product_stock_list.html'            

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_queryset(self):
        date = self.request.GET.get('theDate')
        return super().get_queryset().filter(date=date)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['the_date'] = datetime.datetime.strptime(self.request.GET['theDate'], '%Y-%m-%d')
        context['qs'] = list((data, self.get_queryset().filter(product__source=data[0]))  for data in SOURCES)
        return context

class ProductDetailedView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Product

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False


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
        product.unit_price = request.POST['selling']
        product.date_modified = timezone.now()
        product.save()
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


