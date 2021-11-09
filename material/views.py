# from django.http import request
from django.http.response import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from .models import Article, IssueArticle, RequestArticle
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from staff.models import Employee
from django.db.models import F, Sum


class FormFailure(View):

    def get(self, request, **kwargs):
        context = {
            'msg': kwargs['msg']
        }
        return render(request, 'material/fail.html', context)


class ArticleListView(LoginRequiredMixin, ListView):
    model = Article
    ordering = '-pk'

    def get_queryset(self):
        qs = super().get_queryset().annotate(gross_value=F('value')*F('quantity_balance'))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['gross_value'] = self.get_queryset().aggregate(Sum('gross_value'))['gross_value__sum']
        context['issues'] = IssueArticle.objects.all().order_by('-pk')
        context['requests'] = RequestArticle.available.all().order_by('-pk')
        return context


class ArticleCreateView(LoginRequiredMixin, CreateView):
    model = Article
    fields = ('name', 'description', 'value', 'quantity_in',
    'source')

    def form_valid(self, form):
        form.instance.quantity_balance = form.instance.quantity_in
        return super().form_valid(form)


class ArticleUpdateView(LoginRequiredMixin, UpdateView):
    model = Article
    fields = ('name', 'description', 'value', 'quantity_in',
    'in_date', 'source')

    # def form_valid(self, form):
    #     if form.instance.pack_type == 'Pieces':
    #         form.instance.quantity_per_pack = 0
    #     return super().form_valid(form)


class ArticleDetailView(LoginRequiredMixin, DetailView):
    model = Article


class RequestCreateView(LoginRequiredMixin, CreateView):
    model = RequestArticle
    fields = ('article', 'quantity')

    def form_valid(self, form):
        article = form.instance.article
        if article.quantity_balance >= form.instance.quantity:
            form.instance.request_by = self.request.user
            form.instance.status = True

            #Mailing
            last_num = self.get_queryset().last().id
            send_mail(f'Request for  Article #{str(last_num + 1).zfill(3)}',
            f"A request has been made for {form.instance.quantity} {article.name}. This request is from {Employee.active.get(id=int(self.request.user.username.split('-')[1]))}. An approval is required before issuance.",
            self.request.user.email,
            ['uzo.nwokoro@ozonefl.com', 'uzo.tammy@gmail.com'],
            fail_silently=False,
            )
            
            return super().form_valid(form)
        else:
            messages.info(self.request, 'Request not submitted, Request quantity more than what is available.')
            return redirect('home')


class IssueArticleCreateView(LoginRequiredMixin, CreateView):
    model = IssueArticle
    fields = ('the_request',)   

    def form_valid(self, form):
        article = form.instance.the_request.article
        if article.quantity_balance > form.instance.the_request.quantity:
            article.quantity_balance -= form.instance.the_request.quantity 
            article.save()
            return super().form_valid(form)
        elif article.quantity_balance == form.instance.the_request.quantity:
            article.status = False # article no longer available 
            article.quantity_balance = 0
            article.save()
            return super().form_valid(form)
        else:
            messages.info(self.request, f'Your request for {article} not approved')
            return redirect('article-list')
            

class ArticleRequest(LoginRequiredMixin, View):

    def get(self, request):

        return render(request, 'material/article_request_form.html', context={})