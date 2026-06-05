from django import forms
from .models import JobPosting


class JobPostingForm(forms.ModelForm):
    deadline = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = JobPosting
        fields = [
            'title', 'department', 'location',
            'description', 'requirements',
            'deadline', 'status', 'contact_email',
        ]
        widgets = {
            'description':  forms.Textarea(attrs={'rows': 6}),
            'requirements': forms.Textarea(attrs={'rows': 6}),
        }
