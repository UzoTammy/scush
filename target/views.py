from django.shortcuts import render
from .models import Sales
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin


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
