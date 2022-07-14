from .models import Profile
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib import messages


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    pass
    # messages.success(request, f'{user.get_username()} logged in successfully')

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    pass
    # messages.info(request, f'{user.get_username()} logged out')


# @receiver(pre_save, sender=User)
# def try_something(sender, instance, **kwargs):
#     print(instance.stock_report_date)