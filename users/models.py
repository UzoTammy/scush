from django.db import models
from django.contrib.auth.models import User
from staff. models import Employee
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True)
    stock_report_date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f'{self.user.username} Profile'

    