from django.db import models
from staff.models import Employee
from django.urls import reverse

# Create your models here.
class SalesCenter(models.Model):
    name = models.CharField(max_length=30)
    address = models.CharField(max_length=200)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE)


    def __str__(self):
        return f'{self.name} Sales Center'

    def get_absolute_url(self):
        return reverse('sales-center-detail', kwargs={'pk': self.pk})
