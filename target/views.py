import datetime
from .models import PositionKPIMonthly, Sales
from django.views.generic import View, TemplateView,ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from core import utils as plotter
from trade.models import TradeDaily


class TargetHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'target/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = TradeDaily.objects.filter(date__year=datetime.date.today().year).filter(date__month=10)
        if qs.exists():
            y = [float(obj.margin_ratio()) for obj in qs]
            x = [date.day for date in qs.values_list('date', flat=True)]
            context['margin_plot'] = plotter.margin_graph(x, y)
        return context

class KPIListView(LoginRequiredMixin, ListView):
    model = PositionKPIMonthly
    template_name = 'target/kpi_target_list.html'


class KPICreateView(LoginRequiredMixin, CreateView):
    model = PositionKPIMonthly
    fields = '__all__'
    success_url = reverse_lazy('kpi-list')

class KPIUpdateView(LoginRequiredMixin, UpdateView):
    model = PositionKPIMonthly
    fields = "__all__"
    success_url = reverse_lazy('kpi-list')
    

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
