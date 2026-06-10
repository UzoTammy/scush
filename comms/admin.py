from django.contrib import admin
from .models import Post, Project, Task, Poll, PollOption, PollVote

admin.site.register(Post)
admin.site.register(Project)
admin.site.register(Task)
admin.site.register(Poll)
admin.site.register(PollOption)
admin.site.register(PollVote)
