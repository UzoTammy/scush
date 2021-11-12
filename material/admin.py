from django.contrib import admin
from .models import Article, RequestArticle, IssueArticle

admin.site.register(Article)
admin.site.register(RequestArticle)
admin.site.register(IssueArticle)
