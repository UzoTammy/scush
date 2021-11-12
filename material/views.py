from django.http import request
from django.http.response import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from .models import Article, IssueArticle, RequestArticle
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from staff.models import Employee
from django.db.models import F, Sum
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect


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
        qs = super().get_queryset().filter(status=True)
        qs = qs.annotate(gross_value=F('value')*F('quantity_balance'))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['gross_value'] = self.get_queryset().aggregate(Sum('gross_value'))['gross_value__sum']
        context['requests'] = RequestArticle.objects.filter(status=None).order_by('-pk')
        context['issues'] = IssueArticle.objects.all().order_by('-pk')
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
    'in_date', 'source', 'quantity_balance')

    def form_valid(self, form):
        if form.instance.quantity_balance > 0:
            form.instance.status = True
        return super().form_valid(form)


class ArticleDetailView(LoginRequiredMixin, DetailView):
    model = Article


class RequestCreateView(LoginRequiredMixin, CreateView):
    model = RequestArticle
    fields = ('article', 'quantity')



    def form_valid(self, form):
        article = form.instance.article
        if article.quantity_balance >= form.instance.quantity:
            form.instance.request_by = self.request.user
            form.instance.status = None

            #Mailing
            last_num = self.get_queryset().last().id
            issuer = 'g.motun01@gmail.com'
            sender = self.request.user.email
            send_mail(f'Request for  Article #{str(last_num + 1).zfill(3)}',
            f"A request has been made for {form.instance.quantity} (out of {article.quantity_balance}) {article.name}. This request is from {Employee.active.get(id=int(self.request.user.username.split('-')[1]))}. An approval is required before issuance.",
            '', 
            ['uzo.nwokoro@ozonefl.com', issuer, 'dickson.abanum@ozonefl.com', sender], fail_silently=True)
            return super().form_valid(form)
        else:
            messages.info(self.request, 'Request not submitted, Request quantity more than what is available.')
            return redirect('home')


class IssueArticleCreateView(LoginRequiredMixin, CreateView):
    model = IssueArticle
    fields = []   

    
    def get(self, request, *args, **kwargs):
        qs = RequestArticle.objects.all()
        obj = get_object_or_404(qs, pk=int(kwargs['pk']))
        staff = Employee.active.get(pk=int(str(obj.request_by).split('-')[1]))
        context = {
            'request': obj,
            'staff': staff
        }
        return render(request, 'material/issuearticle_form.html', context=context)
        

    def form_valid(self, form):
        request_obj = RequestArticle.objects.get(pk=self.kwargs['pk'])
        # article = form.instance.the_request.article
        article = request_obj.article
        if article.quantity_balance > request_obj.quantity: #form.instance.the_request.quantity:
            article.quantity_balance -= request_obj.quantity #form.instance.the_request.quantity
            article.save()

            request_obj.status = True
            request_obj.save()

            form.instance.the_request = request_obj
            form.instance.approved_by = self.request.user

            send_mail(f'Request for  Article #{str(request_obj.id).zfill(3)}', 
            f'{request_obj.quantity} {request_obj.article.name} APPROVED', 
            from_email='',
            recipient_list=[request_obj.request_by.email, 'uzo.nwokoro@ozonefl.com', 'g.motun01@gmail.com', 'dickson.abanum@ozonefl.com'],
            fail_silently=True)
            return super().form_valid(form)
        elif article.quantity_balance == request_obj.quantity: #form.instance.the_request.quantity:
            article.status = False # article no longer available 
            article.quantity_balance = 0
            article.save()

            request_obj.status = True
            request_obj.save()

            form.instance.the_request = request_obj
            form.instance.approved_by = self.request.user
            return super().form_valid(form)
        else:
            messages.info(self.request, f'Your request for {article} not approved. Not enough Article(s) to issue')
            return redirect('article-list')
        # return HttpResponse(self.kwargs)
            

class ArticleRequest(LoginRequiredMixin, View):

    def get(self, request):

        return render(request, 'material/article_request_form.html', context={})