# from django.http import request
from django.http import request
from django.http.response import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from .models import Article, IssueArticle, RequestArticle
from django.shortcuts import redirect, render
from django.contrib import messages


class FormFailure(View):

    def get(self, request, **kwargs):
        context = {
            'msg': kwargs['msg']
        }
        return render(request, 'material/fail.html', context)

class ArticleListView(ListView):
    model = Article
    ordering = '-pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issues'] = IssueArticle.objects.all().order_by('-pk')
        context['requests'] = RequestArticle.available.all().order_by('-pk')
        return context


class ArticleCreateView(CreateView):
    model = Article
    fields = ('name', 'description', 'value', 'quantity_in',
    'in_date', 'source')

    def form_valid(self, form):
        form.instance.quantity_balance = form.instance.quantity_in
        return super().form_valid(form)


class ArticleUpdateView(UpdateView):
    model = Article
    fields = ('name', 'description', 'value', 'quantity_in',
    'in_date', 'source')

    # def form_valid(self, form):
    #     if form.instance.pack_type == 'Pieces':
    #         form.instance.quantity_per_pack = 0
    #     return super().form_valid(form)


class ArticleDetailView(DetailView):
    model = Article


class RequestCreateView(CreateView):
    model = RequestArticle
    fields = ('article', 'quantity')

    def form_valid(self, form):
        article = form.instance.article
        if article.quantity_balance >= form.instance.quantity:
            form.instance.request_by = self.request.user
            form.instance.status = True
            return super().form_valid(form)
        else:
            messages.info(self.request, 'Request not submitted, Request quantity more than what is available.')
            return redirect('home')


class IssueArticleCreateView(CreateView):
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
            

class ArticleRequest(View):

    def get(self, request):

        return render(request, 'material/article_request_form.html', context={})