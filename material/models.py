from django.db import models
from djmoney.models.fields import MoneyField
from staff.models import Employee
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class AvailableArticleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=True)

class AvailableRequestArticleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(article__status=True)

class Article(models.Model):
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=100)
    value = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    quantity_in = models.IntegerField(default=0)
    in_date = models.DateField(default=timezone.now)
    source = models.CharField(max_length=20)
    status = models.BooleanField(default=True) #true is available
    image = models.ImageField(default='default.jpg', upload_to='article_pics', blank=True)
    quantity_balance = models.IntegerField(default=0)

    available = AvailableArticleManager()
    objects = models.Manager()
    
    def __str__(self):
        return f'{self.name}-{self.pk}' 


    def get_absolute_url(self):
        return reverse('article-list')

class RequestArticle(models.Model):
    request_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    status = models.BooleanField(default=None, null=True, blank=True) #true: approved, #false: disapproved, #none: pending

    available = AvailableRequestArticleManager()
    objects = models.Manager()
    
    def __str__(self):
        return f'{self.article.name}-{self.id} request'

    def get_absolute_url(self):
        return reverse('home')


class IssueArticle(models.Model):
    the_request = models.ForeignKey(RequestArticle, on_delete=models.CASCADE, verbose_name='Article Requested')
    out_date = models.DateField(default=timezone.now)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.the_request.article} issue'

    def get_absolute_url(self):
        return reverse('article-list')


