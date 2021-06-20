from django.forms import ModelForm
from .models import CreditNote, DebitNote


class CreditForm(ModelForm):
    class Meta:
        model = CreditNote
        exclude = ('status',)


class DebitForm(ModelForm):

    class Meta:
        model = DebitNote
        exclude = ('status',)

