from django.shortcuts import render
from .models import PositionKPIMonthly, Sales
from django.views.generic import View, TemplateView,ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

class TargetHomeView(TemplateView):
    template_name = 'target/home.html'

class KPITargetListView(ListView):
    model = PositionKPIMonthly
    template_name = 'target/kpi_target_list.html'


class KPITargetCreateView(CreateView):
    model = PositionKPIMonthly
    fields = '__all__'
    success_url = reverse_lazy('target-list')


class SalesListView(LoginRequiredMixin, ListView):
    model = Sales


class SalesDetailView(LoginRequiredMixin, DetailView):
    model = Sales


class SalesCreateView(LoginRequiredMixin, CreateView):
    model = Sales
    fields = '__all__'


class SalesUpdateView(LoginRequiredMixin, UpdateView):
    model = Sales
    fields = '__all__'
