import random
import string
import uuid

from django.db import models
from django.urls import reverse
from django.utils import timezone
from staff.models import Employee


class Post(models.Model):
    author = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_created = models.DateField(default=timezone.now)
    title = models.CharField(max_length=50)
    content = models.TextField()
    dispatch = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('comms-post-detail', kwargs={'pk': self.pk})


class Project(models.Model):
    PLANNING = 'PLANNING'
    ACTIVE = 'ACTIVE'
    ON_HOLD = 'ON_HOLD'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (PLANNING, 'Planning'),
        (ACTIVE, 'Active'),
        (ON_HOLD, 'On Hold'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='owned_projects')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PLANNING)
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('comms-project-detail', kwargs={'pk': self.pk})

    @property
    def progress_percent(self):
        total = self.tasks.count()
        if not total:
            return 0
        done = self.tasks.filter(status=Task.DONE).count()
        return round(done * 100 / total)


class Task(models.Model):
    TODO = 'TODO'
    IN_PROGRESS = 'IN_PROGRESS'
    DONE = 'DONE'
    BLOCKED = 'BLOCKED'
    STATUS_CHOICES = [
        (TODO, 'To Do'),
        (IN_PROGRESS, 'In Progress'),
        (DONE, 'Done'),
        (BLOCKED, 'Blocked'),
    ]

    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    PRIORITY_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='created_tasks')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=TODO)
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default=MEDIUM)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.project_id:
            return reverse('comms-project-detail', kwargs={'pk': self.project_id})
        return reverse('comms-task-list')


def _generate_pin():
    return ''.join(random.choices(string.digits, k=6))


class Poll(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='polls')
    created_at = models.DateTimeField(auto_now_add=True)
    closes_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    allow_multiple = models.BooleanField(default=False)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    public_pin = models.CharField(max_length=6, editable=False, default=_generate_pin)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('comms-poll-detail', kwargs={'pk': self.pk})

    def get_public_url(self):
        return reverse('comms-poll-public', kwargs={'token': self.public_token})

    @property
    def total_votes(self):
        return self.votes.count()


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=150)

    def __str__(self):
        return self.text

    @property
    def vote_count(self):
        return self.votes.count()

    @property
    def vote_percent(self):
        total = self.poll.total_votes
        if not total:
            return 0
        return round(self.vote_count * 100 / total)


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True, related_name='poll_votes')
    voter_label = models.CharField(max_length=50, blank=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.option} ({self.voter or self.voter_label or "anonymous"})'
