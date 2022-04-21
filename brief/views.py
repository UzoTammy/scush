from django.views.generic import ListView, CreateView, DetailView, UpdateView
from .models import Post
from staff.models import Employee


class PostListView(ListView):
    model = Post
    ordering = ['-pk']
    paginate_by = 4

    
class PostCreateView(CreateView):
    model = Post
    fields = ('title', 'content')

    def form_valid(self, form):
        try:
            id = int(self.request.user.username.split('-')[1])
        except:
            id = Employee.active.first().id
        form.instance.author = Employee.active.get(id=id)
        return super().form_valid(form)


class PostDetailView(DetailView):
    model = Post

class PostUpdateView(UpdateView):
    model = Post
    fields = '__all__'

