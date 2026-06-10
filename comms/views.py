from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from staff.models import Employee
from .forms import PollForm
from .models import Post, Project, Task, Poll, PollOption, PollVote


def current_employee(request):
    try:
        id = int(request.user.username.split('-')[1])
        return Employee.active.get(id=id)
    except Exception:
        return Employee.active.first()


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    ordering = ['-pk']
    paginate_by = 4


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ('title', 'content')

    def form_valid(self, form):
        form.instance.author = current_employee(self.request)
        return super().form_valid(form)


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    fields = ('title', 'content', 'dispatch')


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    ordering = ['-created_at']


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ('name', 'description', 'status', 'start_date', 'target_date')

    def form_valid(self, form):
        form.instance.owner = current_employee(self.request)
        return super().form_valid(form)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = self.object.tasks.order_by('status', 'due_date')
        return context


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ('name', 'description', 'status', 'start_date', 'target_date')


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    fields = ('title', 'description', 'assigned_to', 'priority', 'status', 'start_date', 'due_date')

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = current_employee(self.request)
        return super().form_valid(form)


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    fields = ('title', 'description', 'assigned_to', 'priority', 'status', 'start_date', 'due_date', 'completed_at')


class TaskStatusUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        status = request.POST.get('status')
        if status in dict(Task.STATUS_CHOICES):
            task.status = status
            task.save()
        return redirect(request.POST.get('next') or task.get_absolute_url())


class TaskListView(LoginRequiredMixin, ListView):
    model = Task

    def get_queryset(self):
        if self.request.GET.get('all'):
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.filter(assigned_to=current_employee(self.request))
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('status', 'due_date')


class PollListView(LoginRequiredMixin, ListView):
    model = Poll
    ordering = ['-created_at']


class PollCreateView(LoginRequiredMixin, CreateView):
    model = Poll
    form_class = PollForm

    def form_valid(self, form):
        form.instance.created_by = current_employee(self.request)
        response = super().form_valid(form)
        for text in form.cleaned_data['options']:
            PollOption.objects.create(poll=self.object, text=text)
        return response


class PollDetailView(LoginRequiredMixin, DetailView):
    model = Poll

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = current_employee(self.request)
        context['has_voted'] = self.object.votes.filter(voter=employee).exists()
        return context


class PollVoteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        poll = get_object_or_404(Poll, pk=pk)
        employee = current_employee(request)
        if poll.is_active and not poll.votes.filter(voter=employee).exists():
            option_ids = request.POST.getlist('option')
            if not poll.allow_multiple:
                option_ids = option_ids[:1]
            for option_id in option_ids:
                option = get_object_or_404(PollOption, pk=option_id, poll=poll)
                PollVote.objects.create(poll=poll, option=option, voter=employee)
        return redirect('comms-poll-results', pk=poll.pk)


class PollResultsView(LoginRequiredMixin, DetailView):
    model = Poll
    template_name = 'comms/poll_results.html'


class PollToggleActiveView(LoginRequiredMixin, View):

    def post(self, request, pk):
        poll = get_object_or_404(Poll, pk=pk)
        poll.is_active = not poll.is_active
        poll.save(update_fields=['is_active'])
        return redirect('comms-poll-list')


class PollPublicAccessView(View):

    def get(self, request, token):
        poll = get_object_or_404(Poll, public_token=token)
        if request.session.get(f'poll_pin_ok_{token}'):
            return redirect('comms-poll-public-vote', token=token)
        return render(request, 'comms/poll_public_access.html', {'poll': poll})

    def post(self, request, token):
        poll = get_object_or_404(Poll, public_token=token)
        pin = request.POST.get('pin', '').strip()
        if pin == poll.public_pin:
            request.session[f'poll_pin_ok_{token}'] = True
            return redirect('comms-poll-public-vote', token=token)
        return render(request, 'comms/poll_public_access.html', {'poll': poll, 'error': 'Incorrect PIN'})


class PollPublicVoteView(View):

    def dispatch(self, request, token, *args, **kwargs):
        self.poll = get_object_or_404(Poll, public_token=token)
        if not request.session.get(f'poll_pin_ok_{token}'):
            return redirect('comms-poll-public', token=token)
        return super().dispatch(request, token, *args, **kwargs)

    def get(self, request, token):
        voted = request.session.get(f'poll_voted_{token}', False)
        return render(request, 'comms/poll_public_vote.html', {'poll': self.poll, 'voted': voted})

    def post(self, request, token):
        if not request.session.get(f'poll_voted_{token}') and self.poll.is_active:
            option_ids = request.POST.getlist('option')
            if not self.poll.allow_multiple:
                option_ids = option_ids[:1]
            for option_id in option_ids:
                option = get_object_or_404(PollOption, pk=option_id, poll=self.poll)
                PollVote.objects.create(poll=self.poll, option=option, voter=None, voter_label='public')
            request.session[f'poll_voted_{token}'] = True
        return redirect('comms-poll-public-vote', token=token)
