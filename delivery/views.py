from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import DeliveryNote
from stock.models import Product
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import (CreateView,
                                       UpdateView,
                                       FormView)
from django.views.generic import (ListView, DetailView, View)
from .form import (DeliveryFormCreate,
                   DeliveryFormDeliver,
                   DeliveryFormReturn)


class DeliveryHomeView(View):

    def get(self, request):
        context = {
            'title': 'Delivery'
        }
        return render(request, 'delivery/home.html', context)


class DeliveryCreateView(CreateView):
    form_class = DeliveryFormCreate
    success_url = reverse_lazy('delivery-home')
    template_name = 'delivery/deliverynote_form.html'


class DeliveryListView(ListView):
    model = DeliveryNote


class DeliveryDetailView(DetailView):
    model = DeliveryNote

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.get_queryset()
        return context


class DeliveryArriveUpdateView(UpdateView):
    model = DeliveryNote
    form_class = DeliveryFormDeliver
    template_name = 'delivery/delivery_form_deliver.html'
    success_url = reverse_lazy('delivery-home')

    def form_valid(self, form):
        form.instance.stage = 'DELIVERED'
        return super().form_valid(form)


class DeliveryReturnUpdateView(FormView):
    model = DeliveryNote
    form_class = DeliveryFormReturn
    template_name = 'delivery/delivery_form_receive.html'
    success_url = reverse_lazy('delivery-home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_obj = Product.objects.get(id=kwargs['pk'])
        product_id = product_obj.id
        product_name = product_obj.name
        product_price = float(product_obj.cost_price.amount)
        product_discount = product_obj.discount
        context['product'] = [product_id, product_name, product_price,
                              product_discount]
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        obj = self.model.objects.get(id=kwargs['pk'])
        context['number'] = obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # context = self.get_context_data(**kwargs)
        json_data = dict()
        total_delivered, total_received, total_amount, total_amount_credit = 0, 0, 0, 0
        for i in range(1, 4):
            product_id = request.POST[f'product_{i}']
            if product_id == '':
                break
            else:
                product_qs = Product.objects.get(id=product_id)
                name = product_qs.name
                price = float(product_qs.cost_price.amount)
                vat = product_qs.vat

                discount = product_qs.discount
                qty_delivered = int(request.POST[f'quantity_delivered_{i}'])
                qty_received = int(request.POST[f'quantity_received_{i}'])
                qty_to_be_credited = qty_delivered - qty_received

                discount_type = product_qs.discount_type

                vattable_amount = qty_delivered * vat/100 * price
                vattable_amount_credit = qty_to_be_credited * vat/100 * price

                if discount_type == 'PP':
                    discount_amount = discount * qty_delivered
                    discount_amount_credit = discount * qty_to_be_credited
                elif discount_type == 'PERCENT':
                    discount_amount = discount/100 * price * qty_delivered
                    discount_amount_credit = discount/100 * price * qty_to_be_credited
                elif discount_type == 'RATIO':
                    discount_amount = qty_delivered/discount * price
                    discount_amount_credit = qty_to_be_credited/discount * price
                else:
                    discount_amount = discount
                    discount_amount_credit = 0
                amount = price * qty_delivered - discount_amount + vattable_amount
                amount_credit = price * qty_to_be_credited - discount_amount_credit + vattable_amount_credit
                json_data.update({
                    f'row_{i}': {
                        'code': f'{product_id}'.zfill(3),
                        'name': name,
                        'delivered': qty_delivered,
                        'received': qty_received,
                        'price': f'{price:,.2f}',
                        'vat': f'{vattable_amount:,.2f}',
                        'discount': f'{discount_amount:,.2f}',
                        'amount': f'{chr(8358)}{amount:,.2f}',
                        }
                })

                total_delivered += qty_delivered
                total_received += qty_received
                total_amount += amount
                total_amount_credit += amount_credit

        json_data['totals'] = {
            'total_delivered': f"{total_delivered:,.0f}",
            'total_received': f"{total_received:,.0f}",
            'total_amount': f"{chr(8358)}{total_amount:,.2f}",
            'total_amount_credit': f"{chr(8358)}{total_amount_credit:,.2f}"
        }

        qs = DeliveryNote.objects.get(id=kwargs['pk'])
        qs.stage = 'RETURNED'
        qs.products = json_data
        if json_data['row_1']['received'] > json_data['row_1']['delivered']:
            messages.warning(request,
                             f"""Quantity received cannot be greater than
the quantity delivered. Data was not saved. Kindly re-enter record""")
        else:
            qs.save()
            messages.success(request, 'Return stage saved successfully, proceed to confirm')
        return redirect('delivery-detail', pk=kwargs['pk'])


class DeliveryConfirm(UpdateView):
    model = DeliveryNote

    def post(self, request, *args, **kwargs):
        qs = self.get_queryset().get(id=kwargs['pk'])
        qs.confirm = True
        qs.save()
        return redirect('delivery-detail', pk=kwargs['pk'])


class DeliveryCredit(UpdateView):
    model = DeliveryNote

    def post(self, request, *args, **kwargs):
        qs = self.get_queryset().get(id=kwargs['pk'])
        qs.credit = True
        qs.save()
        return redirect('delivery-detail', pk=kwargs['pk'])


class DeliveryRemark(UpdateView):
    model = DeliveryNote

    def post(self, request, *args, **kwargs):
        qs = self.get_queryset().get(id=kwargs['pk'])
        qs.remark = f" {request.POST['comment']}"
        qs.save()
        return redirect('delivery-detail', pk=kwargs['pk'])

