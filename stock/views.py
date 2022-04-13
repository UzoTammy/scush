import datetime
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic.base import TemplateView
from django.contrib import messages
from .models import (Product, ProductPerformance, ProductExtension)
from core.models import JsonDataset
from delivery.models import DeliveryNote
from django.db.models import Sum, F
from django.views.generic import (
    View, ListView, DetailView, CreateView, UpdateView, DeleteView)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


permitted_group_name = 'Sales'


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
        if self.request.GET != {}:
            content = obj.dataset
            content['closing-stock-date'] = [self.request.GET['theDate']]
            obj.dataset = content
            obj.save()
        date_string = obj.dataset['closing-stock-date'][0]
        context['current_date'] = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()

        source_list, total_list = list(), list()
        for source in context['sources']:
            qs = ProductExtension.objects.filter(date=context['current_date'], product__source=source)
            qs = qs.annotate(value=F('stock_value')*F('cost_price'))
            source_list.append(qs)
            total_list.append(
                (qs.aggregate(Sum('stock_value'))['stock_value__sum'],
                qs.aggregate(Sum('value'))['value__sum'])
            )
        context['obj'] = source_list
        context['totals'] = [i for i in total_list if i[0] is not None]
        return context


class ReportStockCategory(LoginRequiredMixin, ListView):
    model = Product
    ordering = 'name'

    def get_queryset(self):
        if self.kwargs['source'] == 'All':
            return super().get_queryset().filter(active=True)
        return super().get_queryset().filter(active=True).filter(source=self.kwargs['source'])


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
                cost_price=obj.cost_price
                )
        else:
            qs = ProductExtension.objects.filter(product=obj).filter(date=date_object)
            if qs.exists():
                stock_obj = qs.first()
                stock_obj.stock_value = request.POST['edit_quantity']
                stock_obj.cost_price = obj.cost_price
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
        # selling price gotten from modal form for selling price update only
        product.unit_price = request.POST['selling'] if "selling" in request.POST else product.unit_price
        # Cost price gotten from modal form for cost price update only
        product.cost_price = request.POST['cost'] if "cost" in request.POST else product.cost_price

        date = timezone.datetime(
            timezone.now().year,
            timezone.now().month,
            timezone.now().day,
            hour=11
        )
        product.date_modified = timezone.make_aware(date)
        
        product.save()

        json_data = JsonDataset.objects.get(pk=2).dataset
        date_string = json_data['closing-stock-date'][0]
        date_obj = datetime.datetime.strptime(date_string, "%Y-%m-%d")
        qs = ProductExtension.objects.filter(product=product).filter(date=date_obj)
        if qs.exists():
            stock_obj = qs.first()
            stock_obj.cost_price = product.cost_price
            stock_obj.save()
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
    fields = '__all__'
    template_name = 'stock/report/productextension_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context


class ProductExtensionDetailView(LoginRequiredMixin, DetailView):
    model = ProductExtension
    template_name = 'stock/report/productextension_detail.html'