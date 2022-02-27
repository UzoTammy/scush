from django.db import models
from django.utils import timezone
from staff.models import Employee


class Children(models.Model):
    code = models.IntegerField(primary_key=True)
    staff = models.OneToOneField(Employee, on_delete=models.CASCADE)
    number_kids = models.IntegerField(default=0, blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f'{self.staff.staff.first_name}-{self.code}'

class Question(models.Model):
    code = models.IntegerField(primary_key=True)
    staff = models.OneToOneField(Employee, on_delete=models.CASCADE)
    number_kids = models.IntegerField(default=0)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f'{self.staff.staff.first_name}-{self.code}'
