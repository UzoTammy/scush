from django.contrib import admin
from .models import JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display  = ('title', 'department', 'location', 'status', 'deadline', 'posted_date')
    list_filter   = ('status', 'department')
    search_fields = ('title', 'department')
    list_editable = ('status',)
