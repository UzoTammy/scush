from django.db import models
from django.urls import reverse

class JsonDataset(models.Model):
    name = models.CharField(max_length=30)
    dataset = models.JSONField(verbose_name="Json Data Format")


    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse('json-detail', kwargs={'pk': self.pk})
