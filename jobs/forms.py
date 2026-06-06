from django import forms

from .models import JobPosting, JobApplication, Guarantor


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


class ApplicationInitForm(forms.ModelForm):
    """HR fills this to create a pending application and generate the applicant link."""

    class Meta:
        model = JobApplication
        fields = ['job', 'applicant_name', 'applicant_email']
        labels = {
            'job':             'Job Position',
            'applicant_name':  'Applicant Full Name',
            'applicant_email': 'Applicant Email Address',
        }


class ApplicantForm(forms.ModelForm):
    """Filled by the applicant via their unique token link."""
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = JobApplication
        fields = [
            'applicant_name', 'applicant_email',
            'phone', 'date_of_birth', 'address',
            'education', 'experience', 'cover_letter',
        ]
        labels = {
            'applicant_name':  'Full Name',
            'applicant_email': 'Email Address',
            'education':       'Education / Qualifications',
            'experience':      'Work Experience',
            'cover_letter':    'Cover Letter / Statement of Purpose',
        }
        widgets = {
            'address':      forms.Textarea(attrs={'rows': 3}),
            'education':    forms.Textarea(attrs={'rows': 4}),
            'experience':   forms.Textarea(attrs={'rows': 5}),
            'cover_letter': forms.Textarea(attrs={'rows': 6}),
        }


class GuarantorForm(forms.ModelForm):
    """Filled by the guarantor via their unique token link (Letter of Indemnity)."""
    agreed = forms.BooleanField(
        required=True,
        label=(
            'I have read and understood the terms of this Letter of Indemnity '
            'and I agree to be bound by them.'
        ),
    )

    class Meta:
        model = Guarantor
        fields = [
            'full_name', 'address', 'occupation', 'employer',
            'phone', 'email', 'relationship',
            'id_type', 'id_number', 'agreed',
        ]
        labels = {
            'full_name':    'Full Name',
            'address':      'Residential Address',
            'occupation':   'Occupation / Profession',
            'employer':     'Employer / Place of Business',
            'relationship': 'Relationship to Applicant',
            'id_type':      'Means of Identification',
            'id_number':    'ID Number',
        }
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class HRNotesForm(forms.ModelForm):
    """Quick HR notes update on an application."""

    class Meta:
        model = JobApplication
        fields = ['hr_notes']
        widgets = {'hr_notes': forms.Textarea(attrs={'rows': 4})}
        labels = {'hr_notes': 'HR Notes'}
