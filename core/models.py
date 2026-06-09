from django.db import models
from django.urls import reverse

class JsonDataset(models.Model):
    name = models.CharField(max_length=50)
    dataset = models.JSONField(default=dict, verbose_name="Json Format")

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse('json-detail', kwargs={'pk': self.pk})


class Setting(models.Model):
    TYPE_TEXT   = 'text'
    TYPE_NUMBER = 'number'
    TYPE_DATE   = 'date'
    TYPE_LIST   = 'list'
    VALUE_TYPE_CHOICES = [
        (TYPE_TEXT,   'Text'),
        (TYPE_NUMBER, 'Number'),
        (TYPE_DATE,   'Date'),
        (TYPE_LIST,   'List'),
    ]

    key        = models.CharField(max_length=100, unique=True)
    label      = models.CharField(max_length=100)
    category   = models.CharField(max_length=50)
    value_type = models.CharField(max_length=10, choices=VALUE_TYPE_CHOICES, default=TYPE_TEXT)
    text_value = models.TextField(blank=True, default='')
    list_value = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['category', 'label']

    def __str__(self):
        return f'{self.category} / {self.label}'

    @classmethod
    def get_list(cls, key, default=None):
        try:
            return cls.objects.get(key=key).list_value
        except cls.DoesNotExist:
            return default if default is not None else []

    @classmethod
    def get_value(cls, key, default=''):
        try:
            return cls.objects.get(key=key).text_value
        except cls.DoesNotExist:
            return default



