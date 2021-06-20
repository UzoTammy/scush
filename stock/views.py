from django.shortcuts import render
from .models import Product
from django.views.generic import View
from django.template.loader import get_template
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import (ListView,
                                  DetailView,
                                  CreateView,
                                  UpdateView,
                                  DeleteView)


class MyFirstView(View):

    def get(self, request):

        context = {
            'products': Product.objects.all(),
        }
        response = get_template('stock/myfirst.html').render(context, request)
        return HttpResponse(response)


class ProductListView(ListView):
    model = Product
    ordering = ['name']


class ProductDetailedView(DetailView):
    model = Product


class ProductCreateView(CreateView):
    model = Product
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New'
        return context


class ProductUpdateView(UpdateView):
    model = Product
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update'
        return context


class ProductDeleteView(DeleteView):
    model = Product
    success_url = '/products/list/'
