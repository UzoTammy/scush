from django.db import models
from django.db.models import fields
from django.shortcuts import render
from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView
from .models import Post


class PostListView(ListView):
    model = Post
    ordering = ['-pk']
    paginate_by = 4


class PostCreateView(CreateView):
    model = Post
    fields = '__all__'


class PostDetailView(DetailView):
    model = Post

class PostUpdateView(UpdateView):
    model = Post
    fields = '__all__'

