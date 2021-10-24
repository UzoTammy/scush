from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from .models import SalesCenter
from django.contrib.auth.mixins import LoginRequiredMixin


class SalesCenterListView(LoginRequiredMixin, ListView):
    model = SalesCenter

class SalesCenterDetailView(LoginRequiredMixin, DetailView):
    model = SalesCenter

class SalesCenterCreateView(LoginRequiredMixin, CreateView):
    model = SalesCenter
    fields = '__all__'

class SalesCenterUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesCenter
    fields = '__all__'
    