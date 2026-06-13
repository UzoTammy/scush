# import os
# import csv
# import logging
import datetime
# from pathlib import Path
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
from djmoney.money import Money
from .forms import FormProduct
from pdf.utils import render_to_pdf
from pdf.views import Ozone
from .models import (Product, ProductPerformance, ProductExtension, PriceHistory, Source, Category, StockMovement,
                     StockCountSession, StockCountLine, StockLocation)
from .forms import ProductExtensionUpdateForm, StockMovementForm
from .utils import average_sellout, days_of_cover
from core.models import Setting
from django.db.models import Sum, F, Q, Avg, ProtectedError


permitted_group_name = 'Sales'

def get_date():
    date_string = Setting.get_value('closing_stock_date', '')
    return datetime.datetime.strptime(date_string, '%Y-%m-%d')


def get_top_sellout_products(limit=10):
    """Top sellout products over the last 3 (or 4, across a weekend) days, with their closing stock and profit."""
    if not ProductExtension.objects.exists():
        return [], None

    date2 = ProductExtension.objects.latest('date').date
    date1 = date2 - datetime.timedelta(days=4) if date2.weekday() in (0, 1) else date2 - datetime.timedelta(days=3)

    active_products = Product.objects.filter(active=True).values_list('pk', flat=True).distinct()

    products_qs = []
    for product in active_products:
        product_data = ProductExtension.objects.filter(product=product)
        product_data = product_data.annotate(profit=F('sell_out')*(F('selling_price')-F('cost_price')))

        if not product_data.exists():
            continue

        product_data_recent = product_data.filter(date__range=[date1, date2])

        sellout = product_data_recent.aggregate(Sum('sell_out'))['sell_out__sum'] or 0
        profit = product_data_recent.aggregate(Sum('profit'))['profit__sum'] or 0

        products_qs.append({
            'name': product_data.last().product,
            'sellout': sellout,
            'closing_stock': product_data.last().stock_value,
            'profit': profit,
        })

    return sorted(products_qs, key=lambda x: abs(x['profit']), reverse=True)[:limit], date2


class ProductHomeView(LoginRequiredMixin, View):

    def get(self, request):
        current_stock_value = 0
        total_quantity = 0
        sellout_quantity = 0
        sellout_value = 0
        latest_extension = ProductExtension.objects.order_by('-date').first()
        if latest_extension:
            qs_day = ProductExtension.objects.filter(date=latest_extension.date)
            qs_day = qs_day.annotate(value=F('cost_price') * F('stock_value'))
            current_stock_value = qs_day.aggregate(Sum('value'))['value__sum'] or 0
            total_quantity = qs_day.aggregate(Sum('stock_value'))['stock_value__sum'] or 0
            sellout_quantity = qs_day.aggregate(Sum('sell_out'))['sell_out__sum'] or 0
            sellout_value = qs_day.aggregate(Sum('sales_amount'))['sales_amount__sum'] or 0

        quantity_received = StockMovement.objects.filter(movement_type='RECEIPT').aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Each transfer creates a pair of movements (- at source, + at destination); count only the incoming leg.
        quantity_transferred = StockMovement.objects.filter(movement_type='TRANSFER', quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum'] or 0

        today = timezone.now().date()
        price_changes = PriceHistory.objects.filter(
            date__year=today.year, date__month=today.month
        ).select_related('product', 'changed_by')

        sort_qs_by_sellout, sellout_date = get_top_sellout_products()

        context = {
            'current_stock_value': current_stock_value,
            'total_quantity': total_quantity,
            'sellout_quantity': sellout_quantity,
            'sellout_value': sellout_value,
            'quantity_received': quantity_received,
            'quantity_transferred': quantity_transferred,
            'price_changes': price_changes,
            'sort_qs_by_sellout': sort_qs_by_sellout,
            'sellout_date': sellout_date,
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

        context['sources'] = Source.objects.filter(active=True).values_list('code', flat=True)

        date_string = Setting.get_value('closing_stock_date', '')

        context['msg'] = 'Report Based On Fixed Date'
        if self.request.GET != {}:
            if 'theDate' in self.request.GET.keys():
                date_string = self.request.GET['theDate']
                Setting.objects.filter(key='closing_stock_date').update(text_value=date_string)

            if 'reportDate' in self.request.GET.keys():
                date_string = self.request.GET['reportDate']
                context['msg'] = 'Report Based On Selected Date'

        
        # context['current_date'] = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        context['current_date'] = self.request.user.profile.stock_report_date
        source_list, total_list = list(), list()
        for source in context['sources']:
            qs = ProductExtension.objects.filter(date=context['current_date'], product__source=source)
            qs = qs.annotate(value=F('stock_value')*F('cost_price'))
            qs = qs.annotate(sellout_value=F('sell_out')*F('selling_price'))
            source_list.append(qs.order_by('-value'))
            total_list.append(
                (qs.aggregate(Sum('stock_value'))['stock_value__sum'],
                qs.aggregate(Sum('value'))['value__sum'],
                qs.aggregate(Sum('sell_out'))['sell_out__sum'],
                qs.aggregate(Sum('sellout_value'))['sellout_value__sum'])
            )

        lis = [i for i in source_list if i.exists()]
        context['obj'] = lis
        total_list = [i for i in total_list if i[0] is not None and i[2] is not None]
        context['totals'] = total_list
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
        qs = super().get_queryset()
        if self.kwargs['source'] != 'All':
            qs = qs.filter(source=self.kwargs['source'])
        if self.request.GET.get('show') != 'all':
            qs = qs.filter(active=True)
        return qs

class ProductDetailedView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Product

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        the_date = Setting.get_value('closing_stock_date', '')
        context['theDate'] = datetime.datetime.strptime(the_date, "%Y-%m-%d").date()
        
        product = Product.objects.get(pk=self.kwargs['pk'])
        qs = ProductExtension.objects.filter(product=product).filter(date=context['theDate'])
        
        if qs.exists():
            obj_ext = qs.first()
            context['obj_ext'] = obj_ext
        
        context['is_qs'] = qs.exists()

        """Product velocity displayed in a modal"""
        velocities = {'-1': 'Not Assigned', '0': 'Not Selling', '1': 'Very Low', '2': 'Low',
                                 '3': 'Moderate', '4': "High", '5': 'Very High'}
        key = str(kwargs['object'].velocity) # the value of this object which is the key in the above dictionary
        context['velocity_value'] = velocities[key]
        velocities.pop(key) # remove this key from dictionary to reduce the options
        context['velocities'] = velocities
        return context

    def post(self, request, **kwargs):
        obj = get_object_or_404(Product, pk=self.kwargs['pk'])
        date_string = Setting.get_value('closing_stock_date', '')
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
        elif 'selectVelocity' in request.POST:
            product = get_object_or_404(Product, pk=kwargs['pk'])
            product.velocity = int(request.POST['selectVelocity'])
            product.save()
            messages.info(request, f"Velocity successfully changed in database")
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

    def form_valid(self, form):
        form.instance._changed_by = self.request.user
        return super().form_valid(form)

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

class PriceQuickUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Pick a product, view its current selling price and adjust it up or down."""

    def test_func(self):
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get(self, request):
        context = {'products': Product.objects.filter(active=True).order_by('name')}
        return render(request, 'stock/price_quick_update.html', context)

    def post(self, request):
        product = get_object_or_404(Product, pk=request.POST.get('product'))
        amount = Decimal(request.POST.get('amount') or '0')

        if request.POST.get('direction') == 'decrease':
            new_price = product.unit_price.amount - amount
        else:
            new_price = product.unit_price.amount + amount

        if new_price < 0:
            messages.error(request, 'Selling price cannot be negative.')
        else:
            product.unit_price = new_price
            product._changed_by = request.user
            product.save()
            messages.info(request, f'{product} selling price updated to {product.unit_price} !!!')

        return redirect('price-quick-update')

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
            product._changed_by = request.user
            product.save()
        else:        
            date_string = Setting.get_value('closing_stock_date', '')
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

class PriceHistoryListView(LoginRequiredMixin, ListView):
    model = PriceHistory
    template_name = 'stock/price_history.html'
    paginate_by = 30

    def get_queryset(self):
        self.product = get_object_or_404(Product, pk=self.kwargs['pk'])
        return PriceHistory.objects.filter(product=self.product)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        return context

class StockCardView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'stock/stock_card.html'
    paginate_by = 30

    def get_queryset(self):
        self.product = get_object_or_404(Product, pk=self.kwargs['pk'])
        return StockMovement.objects.filter(product=self.product)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.product
        context['form'] = StockMovementForm(initial={'date': timezone.now().date()})
        context['location_balances'] = [
            {'location': location, 'balance': self.product.stock_balance(location=location)}
            for location in StockLocation.objects.filter(active=True)
        ]
        return context


class StockMovementCreateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.product = product
            movement.created_by = request.user
            movement.save()
            messages.success(request, 'Stock movement recorded successfully')
        else:
            messages.error(request, f'Could not save movement: {form.errors.as_text()}')
        return redirect('stock-card', pk=pk)


class StockCountCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'stock/stock_count_form.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get(self, request):
        sources = Product.objects.filter(active=True).values_list('source', flat=True).distinct()
        querysets = list((source, Product.objects.filter(active=True, source=source)) for source in sources)
        context = {
            'querysets': querysets,
            'date': timezone.now().date(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        session = StockCountSession.objects.create(
            date=request.POST.get('date') or timezone.now().date(),
            note=request.POST.get('note', ''),
            created_by=request.user,
        )
        for product in Product.objects.filter(active=True):
            counted_value = request.POST.get(f'counted_{product.pk}', '').strip()
            if counted_value == '':
                continue
            counted_qty = int(counted_value)
            system_qty = product.stock_balance()
            StockCountLine.objects.create(
                session=session,
                product=product,
                system_qty=system_qty,
                counted_qty=counted_qty,
            )
            variance = counted_qty - system_qty
            if variance != 0:
                StockMovement.objects.create(
                    product=product,
                    movement_type='ADJUSTMENT',
                    quantity=variance,
                    date=session.date,
                    reference=f'Stock Count #{session.pk}',
                    note='Adjustment from physical stock count',
                    created_by=request.user,
                )
        messages.success(request, 'Stock count recorded and adjustments applied')
        return redirect('stock-count-detail', pk=session.pk)


class StockCountListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = StockCountSession
    template_name = 'stock/stock_count_list.html'
    paginate_by = 30

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False


class StockCountDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = StockCountSession
    template_name = 'stock/stock_count_detail.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False


class StockTransferView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'stock/stock_transfer.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get(self, request):
        context = {
            'locations': StockLocation.objects.filter(active=True),
            'products': Product.objects.filter(active=True),
            'date': timezone.now().date(),
            'transfers': StockMovement.objects.filter(movement_type='TRANSFER').order_by('-date', '-created_at')[:30],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        product = get_object_or_404(Product, pk=request.POST['product'])
        from_location = get_object_or_404(StockLocation, pk=request.POST['from_location'])
        to_location = get_object_or_404(StockLocation, pk=request.POST['to_location'])
        quantity = int(request.POST['quantity'])
        date = request.POST.get('date') or timezone.now().date()
        note = request.POST.get('note', '')

        if from_location == to_location:
            messages.error(request, 'Source and destination locations must be different')
        elif quantity <= 0:
            messages.error(request, 'Transfer quantity must be greater than zero')
        else:
            reference = f'Transfer {from_location} -> {to_location}'
            StockMovement.objects.create(
                product=product, movement_type='TRANSFER', quantity=-quantity,
                date=date, location=from_location, reference=reference, note=note, created_by=request.user,
            )
            StockMovement.objects.create(
                product=product, movement_type='TRANSFER', quantity=quantity,
                date=date, location=to_location, reference=reference, note=note, created_by=request.user,
            )
            messages.success(request, f'Transferred {quantity} x {product} from {from_location} to {to_location}')

        return redirect('stock-transfer')


class StockLocationAddView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        if name:
            StockLocation.objects.get_or_create(name=name, defaults={'address': address})
        return redirect('settings')


class StockLocationRenameView(LoginRequiredMixin, View):
    def post(self, request, pk):
        location = get_object_or_404(StockLocation, pk=pk)
        location.name = request.POST.get('name', location.name).strip()
        location.address = request.POST.get('address', '').strip()
        location.save()
        return redirect('settings')


class StockLocationToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        location = get_object_or_404(StockLocation, pk=pk)
        location.active = not location.active
        location.save()
        return redirect('settings')


class StockLocationRemoveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        location = get_object_or_404(StockLocation, pk=pk)
        try:
            location.delete()
        except ProtectedError:
            messages.error(request, f"Cannot remove location '{location}' — it is still referenced by stock movements.")
        return redirect('settings')


class SourceDetailUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        source = get_object_or_404(Source, pk=pk)
        source.contact_person = request.POST.get('contact_person', '').strip()
        source.phone = request.POST.get('phone', '').strip()
        source.email = request.POST.get('email', '').strip()
        try:
            source.lead_time_days = int(request.POST.get('lead_time_days') or 0)
        except ValueError:
            source.lead_time_days = 0
        source.save()
        return redirect('settings')


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
    paginate_by = 30

    def get_queryset(self):
        return Product.objects.filter(active=True).order_by('name')

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
        
        # if request.FILES:
        #     myfile = request.FILES['fileName']
        #     # os.path.join(settings.STATIC_ROOT, 'stock')
        #     dirname = os.path.dirname(__file__)
        #     fs = FileSystemStorage(location=os.path.join(dirname, 'status'))
            
        #     for file in os.listdir(fs.location):
        #         path = os.path.join(fs.location, file)
        #         if os.path.exists(path):
        #             os.remove(path)
            
        #     filename = fs.save(myfile.name, myfile)
        #     messages.info(request, f'{filename} uploaded successfully')
        # else:
        date = request.POST['date']
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')

        user = User.objects.get(username=kwargs['user'])
        user.profile.stock_report_date = date_obj.date()
        user.save()
        messages.info(request, f'Date has been set to {date_obj.strftime("%d-%b-%Y")} successfully !!!')
        
        return super().get(request, **kwargs)

# class BulkUpdateStock(LoginRequiredMixin, UserPassesTestMixin, View):

#     def test_func(self):
#         """if user is a member of the group Sales then grant access to this view"""
#         if self.request.user.groups.filter(name=permitted_group_name).exists():
#             return True
#         return False

#     def get(self, request, **kwargs):
#         dirname = os.path.join(os.path.dirname(__file__), 'status')
#         filename = os.listdir(dirname)[0]
#         filepath = os.path.join(dirname, filename)

#         context, msg = dict(), list()
#         with open(filepath, 'r') as rf:
#             content = csv.reader(rf)
#             headings = [next(content), next(content), next(content), next(content), next(content)]
#             qualifier = [True if len(headings[0]) == 7 else False]
#             if qualifier[0] is False:
#                 msg.append('Number of columns must be seven')
#             qualifier.append(headings[2][0].split()[1] == headings[2][0].split()[3])
#             if qualifier[1] is False:
#                 msg.append("File's date is missing or date is more than one day")
#             qualifier.append(headings[3][0] == 'All Items' and headings[3][1] == 'All MC')
#             if qualifier[2] is False:
#                 msg.append("File may not have taken all items or all MCs")
#             qualifier.append(all(headings[-1]) and headings[-1][-1]=='Cost Price' and headings[-1][0]=='Product code')
#             if qualifier[3] is False:
#                 msg.append("File columns may differ from what is expected")

#             if all(qualifier):
#                 date_string = headings[2][0].split()[1]
#                 date_obj = datetime.date(int(date_string.split('-')[2]), int(date_string.split('-')[1]), int(date_string.split('-')[0]))
                
#                 try:
#                     dataset = [{
#                         'id': int(record[0]),
#                         'product': Product.objects.get(pk=int(record[0])) if Product.objects.filter(pk=int(record[0])).exists() else 'Product not found',
#                         'item': record[1],
#                         'sellout': int(string_float(record[2])),
#                         'selling_price': string_float(record[3]),
#                         'sales_amount': string_float(record[4]),
#                         'closing_balance': int(string_float(record[5])),
#                         'cost_price': string_float(record[6])
#                     } for record in content if record[0] != '']  
                    
#                     context = {
#                         'date': date_obj,
#                         'filename': filepath,
#                         "dataset": dataset,
#                     }
                    
#                     post_dataset = list()
#                     lock_save = False
#                     for data in dataset:
#                         X = data.copy()
#                         product = X.pop('product')
#                         del X['item']
#                         try:
#                             product.id
#                         except:
#                             messages.warning(request, "This dataset is not fit to go into database !!!")
#                             lock_save = True
#                             break
#                         else:
#                             X.update({'id': product.id})
#                             post_dataset.append(X)
#                     context['post_dataset'] = post_dataset
#                 except:
#                     messages.warning(request, "CSV not well prepared for the database")
#                     lock_save = True
#         context['lock_save'] = lock_save
#         context['qualifier'] = all(qualifier) #boolean 
#         context['msg'] = msg #list
#         return render(request, 'stock/packs/bulk_update.html', context=context)
        

#     def post(self, request, **kwargs):
#         # fetch from post request the date and the list of data for update to the model
#         date = datetime.datetime.strptime(request.POST['date'], '%B %d, %Y').date()
#         content = request.POST['content']
#         list_data = eval(content)

#         #note: check the record dictionary for adequacy
#         for record in list_data:
#             try:
#                 obj, created = ProductExtension.objects.update_or_create(
#                     product_id=record['id'],
#                     date=date,
#                     defaults={
#                         'cost_price': record['cost_price'],
#                         'selling_price': record['selling_price'],
#                         'stock_value': record['closing_balance'],
#                         'sell_out': record['sellout'],
#                         'sales_amount': record['sales_amount'],
#                     }
#                 )
#             except:
#                 messages.warning(request, f"{obj} failed to join database!!!. Process is hereby aborted")
#                 return self.get(request, **kwargs)
#         messages.success(request, f"All records updated or saved into database !!!")
#         return self.get(request, **kwargs)

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

    def extreme_product(self, data, func=max, value_cast=lambda v: v):
        """Pick the product tuple with the max/min value from a (product_pk, value) list.

        Returns a ('-', 0) placeholder when the data is empty, so that a day/month/year
        with no qualifying records (e.g. zero sales) does not raise on max()/min().
        """
        if not data:
            return ('-', 0)
        item = func(data, key=lambda x: x[1])
        return (Product.objects.get(pk=item[0]).nickname(), value_cast(item[1]))

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
            
            # A product is "low stock" once its reported balance falls to/below its
            # configured reorder point (or min stock level if no reorder point is set).
            # Products with neither configured fall back to the old fixed threshold.
            low_stock_filter = (
                Q(product__reorder_point__gt=0, stock_value__lte=F('product__reorder_point')) |
                Q(product__reorder_point=0, product__min_stock_level__gt=0, stock_value__lte=F('product__min_stock_level')) |
                Q(product__reorder_point=0, product__min_stock_level=0, stock_value__lt=10)
            )

            context['low_stock'] = qs_day.filter(stock_value__gt=0).filter(low_stock_filter)
            context['no_sellout'] = qs_day.filter(stock_value__gt=0).filter(sell_out=0)
            context['low_sellout'] = qs_day.filter(stock_value__gt=0).filter(sell_out__lt=10).exclude(sell_out=0)

            # Sorted by days since last sale, descending (longest-idle products first; "Never" sold first of all)
            context['no_sellout_sorted'] = sorted(
                context['no_sellout'],
                key=lambda record: record.product.days_since_last_sale() if record.product.days_since_last_sale() is not None else float('inf'),
                reverse=True,
            )

            context['no_stock_month'] = self.month_process(qs_month, qs_month.filter(stock_value__lte=0))
            context['low_stock_month'] = self.month_process(qs_month, qs_month.filter(stock_value__gt=0).filter(low_stock_filter))
            zero_sellout = self.month_process(qs_month, qs_month.filter(stock_value__gt=0).filter(sell_out=0))
            context['low_sellout_month'] = self.month_process(qs_month, qs_month.filter(stock_value__gt=0).filter(sell_out__lt=10).exclude(sell_out=0))

            context['no_sellout_month'] = zero_sellout
            if zero_sellout:
                """Locked down capital is the value in stock that have not sold even ones in the month"""
                total = sum([obj.stock_value * obj.cost_price for obj in zero_sellout])
                context['ldc'] = float(total.amount)
            else:
                context['ldc'] = 0

            total_products = context['products'].count()
            context['availability_ratio'] = 100 * (1 - context['no_stock'].count()/total_products) if total_products else 0
            context['av_color'] = self.color(context['availability_ratio'])

            stocked_products = total_products - context['no_stock'].count()
            context['movement_ratio'] = 100 * (1 - context['no_sellout'].count()/stocked_products) if stocked_products > 0 else 0
            context['mv_color'] = self.color(context['movement_ratio'])
            
        if ProductExtension.objects.exists():
            latest_date = ProductExtension.objects.latest('date').date
            context['current_date'] = latest_date
            product_extension = ProductExtension.objects.filter(sell_out__gt=0).exclude(product__name__icontains='Empty')
            # Most sold out product of the day
            qs_data = product_extension.filter(date=latest_date)
            # get a tuple of the product and the sellout
            data = qs_data.values_list('product', 'sell_out')
            context['highest_sellout_day'] = self.extreme_product(data)

            # Most soldout product of the month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month).filter(sell_out__gt=0)
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_sellout_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sell_out'))['sell_out__sum'])
                for product in products
            ]
            context['highest_sellout_month'] = self.extreme_product(most_sellout_list)

            """Most soldout product of the year"""
            qs_data = product_extension.filter(date__year=latest_date.year)
            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_sellout_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sell_out'))['sell_out__sum'])
                for product in products
            ]
            context['highest_sellout_year'] = self.extreme_product(most_sellout_list)
            
            """This section is for the most profitable"""
            # For the latest date
            qs_data = product_extension.filter(date=latest_date)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))
            
            # get a tuple of the product and the sellout
            data = qs_data.values_list('product', 'profit')
            context['most_profitable_day'] = self.extreme_product(data)

            # for the latest date's month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('profit'))['profit__sum'])
                for product in products
            ]
            context['most_profitable_month'] = self.extreme_product(most_profit_list)

            # for the latest date's year
            qs_data = product_extension.filter(date__year=latest_date.year)
            qs_data = qs_data.annotate(profit = F('sell_out')*(F('selling_price') - F('cost_price')))

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sellout
            most_profit_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('profit'))['profit__sum'])
                for product in products
            ]
            context['most_profitable_year'] = self.extreme_product(most_profit_list)
            
            # Margins
            # 1. the product with the best margin
            qs_data = product_extension.filter(date=latest_date).filter(sell_out__gt=0)
            qs_data = qs_data.annotate(margin=F('selling_price') - F('cost_price'))
            
            # get a tuple of the product and its margin (selling_price - cost_price)
            data = qs_data.values_list('product', 'margin')

            context['best_margin_day'] = self.extreme_product(data, func=max)

            #2. the product with the worst margin
            context['worst_margin_day'] = self.extreme_product(data, func=min)

            #3 Average margin
            qs_data = qs_data.annotate(profit=F('sell_out') * F('margin'))
            total_profit = qs_data.aggregate(Sum('profit'))['profit__sum']
            total_sales = qs_data.aggregate(Sum('sales_amount'))['sales_amount__sum']
            context['average_margin'] = float(total_profit/total_sales) * 100 if total_sales else 0
            
            """The gross sales"""
            #1. Product with the highest gross sales value
            qs_data = product_extension.filter(date=latest_date)
            
                # get a tuple of the product and the sales
            data = qs_data.values_list('product', 'sales_amount')
            context['most_sales_day'] = self.extreme_product(data, value_cast=float)

            #2. Product with the highest GSV in the month
            qs_data = product_extension.filter(date__year=latest_date.year).filter(date__month=latest_date.month)

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sales
            most_sales_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sales_amount'))['sales_amount__sum'])
                for product in products
            ]
            context['most_sales_month'] = self.extreme_product(most_sales_list, value_cast=float)

            #3. Product with the highest GSV for the year
            qs_data = product_extension.filter(date__year=latest_date.year)

            products = qs_data.values_list('product', flat=True).distinct() # product pk only
            # create a list of tuple of products and its aggregate sales
            most_sales_list = [
                (product, qs_data.filter(product=product).aggregate(Sum('sales_amount'))['sales_amount__sum'])
                for product in products
            ]
            context['most_sales_year'] = self.extreme_product(most_sales_list, value_cast=float)
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
            active_products_list = Product.objects.filter(active=True)
            active_products = active_products_list.values_list('pk', flat=True).distinct().order_by('source')

            """Sellout Velocity process starts here. Velocity type ranges from -1 to 5.
            -1 - Not designated, 0 - No sellout, 1 - very low sellout, 2 - low sellout
            3 - moderate, 4 - high sellout and 5 - very high sellout.
            output: [(v1, qs1), (v2, qs2), (v3, qs3)]
            """
            
            product_list_for_velocity = [(i, active_products_list.filter(velocity=i).values_list('pk', flat=True)) 
                                         for i in range(-1, 6)]
        else:
            return context

        if ProductExtension.objects.exists():
            date2 = ProductExtension.objects.latest('date').date
            qs_list = list((i, ProductExtension.objects.filter(date=date2).filter(product__velocity=i)) for i in range(-1, 6))
            stack = list()
            for item in qs_list:
                if item[1].exists():
                    qs = item[1].annotate(sv=F('cost_price')*F('stock_value'))
                    value = (qs.aggregate(Sum('sv'))['sv__sum'], qs)
                else:
                    value = (Decimal('0'), qs.none())
                stack.append((item[0], Money(value[0], 'NGN'), value[1]))
            stack.sort(key=lambda x:x[0])  
            
            percent_stack = list()
            total = sum(i[1] for i in stack)
            for item in stack:
                percent_stack.append(100*item[1]/total)
            
            haystack = list()
            for item in stack:
                if item[0] == -1:
                    haystack.append(item[1])
                    sums = Money(0, "NGN")
                elif item[0] == 0 or item[0] == 1 or item[0] == 2:
                    sums += item[1]
                elif item[0] == 3:
                    haystack.append(sums)
                    haystack.append(item[1])
                    sums = Money(0, "NGN")
                else:
                    sums += item[1]
            haystack.append(sums)
            
            context['total_stock_value'] = sum(i[1] for i in stack)
            context['stack'] = stack
            context['percent_stack'] = percent_stack
            context['haystack'] = haystack
            
        else:
            return context

        for product in active_products:
            product_data = ProductExtension.objects.filter(product=product)

            if product_data.exists():
                product_obj = Product.objects.get(pk=product)
                closing_stock = product_data.last().stock_value
                avg_7d = average_sellout(product_obj, 7)
                avg_30d = average_sellout(product_obj, 30)
                cover = days_of_cover(closing_stock, avg_7d)

                all_products_qs.append({
                    'name': product_data.first().product,
                    'avg_7d': avg_7d,
                    'avg_30d': avg_30d,
                    'closing_stock': closing_stock,
                    'days_of_cover': cover,
                    'status': product_obj.stock_status(),
                    })

        context['current_date'] = date2
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

class StockBalancingView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'stock/balancing/home.html'

    def test_func(self):
        """if user is a member of the group Sales then grant access to this view"""
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        understock, overstock, unset = list(), list(), list()

        for product in Product.objects.filter(active=True):
            stock = product.current_stock()
            status = product.stock_status()

            if status == 'UNSET':
                unset.append({'product': product, 'closing_stock': stock})
            elif status == 'LOW':
                suggested_qty = product.reorder_qty or max(product.max_stock_level - (stock or 0), 0)
                understock.append({
                    'product': product,
                    'closing_stock': stock,
                    'reorder_point': product.reorder_point,
                    'suggested_qty': suggested_qty,
                })
            elif status == 'OVER':
                overstock.append({
                    'product': product,
                    'closing_stock': stock,
                    'max_stock_level': product.max_stock_level,
                    'excess_qty': stock - product.max_stock_level,
                })

        context['understock'] = understock
        context['overstock'] = overstock
        context['unset'] = unset
        return context


class ProductLevelUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Update only the stock-level fields of a product, from the Stock Balancing page."""

    def test_func(self):
        if self.request.user.groups.filter(name=permitted_group_name).exists():
            return True
        return False

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        for field in ('min_stock_level', 'max_stock_level', 'reorder_point', 'reorder_qty'):
            value = request.POST.get(field, '').strip()
            setattr(product, field, int(value) if value else 0)

        product._changed_by = request.user
        product.save()
        messages.info(request, f'{product} stock levels updated !!!')
        return redirect('stock-balancing')


# ── Category settings (manage from Settings page) ─────────────────────────────

class CategoryAddView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        if name:
            Category.objects.get_or_create(name=name)
        return redirect('settings')


class CategoryRenameView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        name = request.POST.get('name', '').strip()
        if name:
            category.name = name
            category.save()
        return redirect('settings')


class CategoryToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.active = not category.active
        category.save()
        return redirect('settings')


class CategoryRemoveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        try:
            category.delete()
        except ProtectedError:
            messages.error(request, f"Cannot remove category '{category}' — it is still used by one or more products.")
        return redirect('settings')


# ── Source settings (manage from Settings page) ───────────────────────────────

class SourceAddView(LoginRequiredMixin, View):
    def post(self, request):
        code = request.POST.get('code', '').strip()
        label = request.POST.get('label', '').strip()
        if code:
            Source.objects.get_or_create(pk=code, defaults={'label': label})
        return redirect('settings')


class SourceRenameView(LoginRequiredMixin, View):
    def post(self, request, pk):
        source = get_object_or_404(Source, pk=pk)
        source.label = request.POST.get('label', '').strip()
        source.save()
        return redirect('settings')


class SourceToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        source = get_object_or_404(Source, pk=pk)
        source.active = not source.active
        source.save()
        return redirect('settings')


class SourceRemoveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        source = get_object_or_404(Source, pk=pk)
        try:
            source.delete()
        except ProtectedError:
            messages.error(request, f"Cannot remove source '{source}' — it is still used by one or more products.")
        return redirect('settings')
