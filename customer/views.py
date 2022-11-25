from django.urls import reverse_lazy
from .models import CustomerProfile
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (CreateView,
                                  ListView,
                                  DetailView,
                                  UpdateView,
                                  DeleteView,
                                  TemplateView)

class CustomerHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/customer_home.html'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customers = CustomerProfile.objects.all()
        
        if customers.exists():
            qs = customers.filter(active=True)
            context['customers'] = customers
            context['active_customers'] = customers.filter(active=True)
            context['inactive_customers'] = customers.filter(active=False)
            context['lagos_customers'] = qs.filter(region='LOS')
            context['outside_lagos_customers'] = qs.filter(region='OLS')
            context['diaspora_customers'] = qs.filter(region='DSP')
            context['badagry_qs'] = qs.filter(cluster='BAD')
            context['barracks_qs'] = qs.filter(cluster='BAR')
            context['festac_qs'] = qs.filter(cluster='FES')
            context['lagos_island_qs'] = qs.filter(cluster='LIS')
            context['okoko_qs'] = qs.filter(cluster='OKO')
            context['omonile_qs'] = qs.filter(cluster='OMO')
            context['satellite_qs'] = qs.filter(cluster='SAT')
            context['trade_fair_qs'] = qs.filter(cluster='TRF')

            # This is classification
            qs_list = CustomerProfile.objects.values_list('classification', flat=True).distinct() #qs_list
            classes = {
                'OWP': '1-Way', 'ALL': 'All', 'RTW': 'Ret+Wine', 'WIN': 'Wine',
                'OWW': '1-Way+Wine', 'ROW':'Ret+1-Way', 'RTN': 'Returnable'
            }
            result = [(klass, qs.filter(classification=klass)) for klass in qs_list] # list of querysets
            classifications = [
                {'name': classes.get(topple[0]), 'count': topple[1].count, 'sales': 20} 
            for topple in result
            ]
            
            context['classes'] = classifications
        return context


class CustomerListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomerProfile
    ordering = ['-pk']

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False
    
    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        context['title'] = 'home'
        if self.get_queryset():
            qs = self.get_queryset().filter(active=True)
            if self.kwargs['select'] == 'active':
                context['customers'] = self.get_queryset().filter(active=True)
            elif self.kwargs['select'] == 'inactive':
                context['customers'] = self.get_queryset().filter(active=False)
            elif self.kwargs['select'] == 'lagos':
                context['customers'] = qs.filter(region='LOS')
            elif self.kwargs['select'] == 'diaspora':
                context['customers'] = qs.filter(region='DSP')
            elif self.kwargs['select'] == 'outside_lagos':
                context['customers'] = qs.filter(region='OLS')
            else:
                context['customers'] = self.get_queryset()

        return context


class CustomerClusterView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/customer_cluster.html'
    
    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_staff:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = CustomerProfile.objects.filter(active=True)
        clusters = {
            'badagry': 'BAD','barracks': 'BAR', 'lagos-island':'LIS', 'festac': 'FES', 
            'okoko': 'OKO', 'omonile': 'OMO','satellite': 'SAT', 'trade-fair': 'TRF'
        }

        context['cluster'] = qs.filter(cluster=clusters.get(kwargs['cluster']))
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = CustomerProfile


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = CustomerProfile
    fields = "__all__"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "New"
        context['btn_text'] = 'Create'
        return context


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerProfile
    fields = "__all__"
    # form_class = CustomerUpdateProfileForm

    def get(self, request, *args, **kwargs):
        obj = self.get_queryset().get(pk=kwargs['pk'])
        #get the string of section & convert to list
        # section = ast.literal_eval(obj.section)
        return super().get(request, *args, **kwargs)
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Update"
        context['btn_text'] = 'Update'
        return context


class CustomerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomerProfile
    success_url = reverse_lazy('customer-list-all')  # '/','/index/'

    def test_func(self):
        # customer = self.get_object()
        if self.request.user.is_superuser:
            return True
        return False


class RequestHome(LoginRequiredMixin, TemplateView):
    template_name = 'customer/requests/request.html'


class CustomerHelpView(TemplateView):
    template_name = 'customer/customer_help.html'