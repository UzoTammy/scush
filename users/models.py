import uuid
import datetime
from django.db import models
from django.contrib.auth.models import User
from staff.models import Employee
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True)
    stock_report_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f'{self.user.username} Profile'


def _invite_expiry():
    return timezone.now() + datetime.timedelta(days=7)


class UserInvite(models.Model):
    """A one-time link an Administrator generates so a brand-new person can
    set up their own account without needing to log in first."""
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invites')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_invite_expiry)
    used = models.BooleanField(default=False)
    used_by = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invite_used')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Invite → {self.email}'

    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at

