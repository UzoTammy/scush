from django import forms
from .models import Poll


class PollForm(forms.ModelForm):
    options = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': 'One option per line'}),
        help_text='Enter each poll option on its own line (at least 2).',
    )

    class Meta:
        model = Poll
        fields = ('title', 'description', 'closes_at', 'allow_multiple', 'options')
        widgets = {
            'closes_at': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_options(self):
        lines = [line.strip() for line in self.cleaned_data['options'].splitlines() if line.strip()]
        if len(lines) < 2:
            raise forms.ValidationError('Provide at least two options.')
        return lines
