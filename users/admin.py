from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Register your models here.
admin.site.register(Profile)


class NoAddUserAdmin(UserAdmin):
    """Invite User (users:user-invite-create) is the single source of
    account creation — block Django Admin's own "Add user" as another way
    around that. Viewing/editing/deleting existing users is unaffected."""

    def has_add_permission(self, request):
        return False


admin.site.unregister(User)
admin.site.register(User, NoAddUserAdmin)
