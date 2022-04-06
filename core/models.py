from django.db import models
from django.urls import reverse

class JsonDataset(models.Model):
    name = models.CharField(max_length=50)
    dataset = models.JSONField(default=dict, verbose_name="Json Format")


    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse('json-detail', kwargs={'pk': self.pk})
