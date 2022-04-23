from datetime import timezone
from django.db import models
from django.urls.base import reverse
from staff.models import Employee
from django.utils import timezone


class Post(models.Model):
    author = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_created = models.DateField(default=timezone.now)
    title = models.CharField(max_length=50)
    content = models.TextField()
    dispatch = models.BooleanField(default=False)


    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})