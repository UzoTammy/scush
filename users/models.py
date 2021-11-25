from django.db import models
from django.contrib.auth.models import User
from staff. models import Employee

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE, default=2)
    # image = models.ImageField(default='default.jpg', upload_to='profile_pics')

    # bio = models.TextField(blank=True, null=True)
    # facebook_url = models.CharField(max_length=255, blank=True, null=True)
    # twitter_url = models.CharField(max_length=255, blank=True, null=True)
    # instagram_url = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    