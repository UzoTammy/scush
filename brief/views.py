from django.views.generic import ListView, CreateView, DetailView, UpdateView
from .models import Post
from staff.models import Employee
from django.contrib.auth.mixins import LoginRequiredMixin

class PostListView(LoginRequiredMixin, ListView):
    model = Post
    ordering = ['-pk']
    paginate_by = 4

    
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ('title', 'content')

    def form_valid(self, form):
        try:
            id = int(self.request.user.username.split('-')[1])
        except Exception:
            id = Employee.active.first().id
        form.instance.author = Employee.active.get(id=id)
        return super().form_valid(form)


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    fields = '__all__'

