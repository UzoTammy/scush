import datetime

import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone

from .forms import UserRegisterForm
from .models import UserInvite

@pytest.mark.parametrize(
    "username, email, password, password2, validity",
    [
        ('user1', 'user1@email.com', 'Greatword12', 'Greatword12', True),
        ('user2', 'user2@email.com', 'user22', 'user12', False), # password mismatch
        ('user3', 'user3@email.com', '', 'user33', False), #no first password
        ('user4', 'user4@email.com', 'user44', '', False), #no second password
        ('user1', 'user1emailcom', 'Greatword12', 'Greatword12', False), # Invalid email
    ]
)
@pytest.mark.django_db
def test_registeration_form(client, username, email, password, password2, validity):
    form = UserRegisterForm(
        data = {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password2
        }
    )
    assert form.is_valid() is validity


@pytest.fixture
def admin_user(db, user_in_group_factory):
    return user_in_group_factory('Administrator', username='reg_admin')


@pytest.mark.django_db
class TestRegisterView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('register'))
        assert response.status_code == 302

    def test_non_admin_forbidden(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('register'))
        assert response.status_code == 403

    def test_administrator_group_member_allowed(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('register'))
        assert response.status_code == 200

    def test_superuser_without_group_allowed(self, client, superuser):
        """Regression: the sidebar link is shown to superusers (core/base.html
        gates on user.is_superuser), but the view used to check Administrator
        group membership only — a superuser outside that group got a 403
        clicking a link the UI told them they could use."""
        client.force_login(superuser)
        response = client.get(reverse('register'))
        assert response.status_code == 200

    def test_valid_registration_creates_user(self, client, admin_user):
        client.force_login(admin_user)
        response = client.post(reverse('register'), data={
            'username': 'newstaffuser', 'email': 'newstaff@example.com',
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        assert response.status_code == 302
        assert User.objects.filter(username='newstaffuser').exists()


# ── UserInvite model ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserInviteModel:
    def test_fresh_invite_is_valid(self):
        invite = UserInvite.objects.create(email='a@example.com')
        assert invite.is_valid() is True

    def test_expired_invite_is_invalid(self):
        invite = UserInvite.objects.create(email='a@example.com')
        invite.expires_at = timezone.now() - datetime.timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        assert invite.is_valid() is False

    def test_used_invite_is_invalid_even_if_not_expired(self):
        invite = UserInvite.objects.create(email='a@example.com', used=True)
        assert invite.is_valid() is False


# ── invite_create view: permission gate + creation ──────────────────────────

@pytest.mark.django_db
class TestInviteCreateView:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('user-invite-create'))
        assert response.status_code == 302

    def test_non_admin_forbidden(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('user-invite-create'))
        assert response.status_code == 403

    def test_administrator_group_member_allowed(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('user-invite-create'))
        assert response.status_code == 200

    def test_superuser_allowed(self, client, superuser):
        client.force_login(superuser)
        response = client.get(reverse('user-invite-create'))
        assert response.status_code == 200

    def test_post_creates_invite_tied_to_creator(self, client, admin_user):
        client.force_login(admin_user)
        response = client.post(reverse('user-invite-create'), data={'email': 'invitee@example.com'})
        assert response.status_code == 302
        invite = UserInvite.objects.get(email='invitee@example.com')
        assert invite.created_by == admin_user
        assert invite.is_valid() is True


# ── invite_delete view: admin can retract a link ────────────────────────────

@pytest.mark.django_db
class TestInviteDeleteView:
    def test_admin_can_delete_a_pending_invite(self, client, admin_user):
        invite = UserInvite.objects.create(email='a@example.com')
        client.force_login(admin_user)
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is False

    def test_deleted_invite_link_404s_afterward(self, client, admin_user):
        invite = UserInvite.objects.create(email='a@example.com')
        token = invite.token
        client.force_login(admin_user)
        client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))

        response = client.get(reverse('register-invite', kwargs={'token': token}))
        assert response.status_code == 404

    def test_deleting_a_used_invite_does_not_touch_the_created_user(self, client, admin_user):
        invite = UserInvite.objects.create(email='invitee@example.com')
        client.post(reverse('register-invite', kwargs={'token': invite.token}), data={
            'username': 'keepme', 'email': 'invitee@example.com',
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        invite.refresh_from_db()
        client.logout()
        client.force_login(admin_user)
        client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert User.objects.filter(username='keepme').exists() is True

    def test_non_admin_forbidden(self, client, new_user):
        invite = UserInvite.objects.create(email='a@example.com')
        client.force_login(new_user)
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 403
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True

    def test_anonymous_redirected_to_login(self, client):
        invite = UserInvite.objects.create(email='a@example.com')
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True

    def test_get_does_not_delete(self, client, admin_user):
        """GET is a safe method — only a POST (the confirm-dialog form submit) deletes."""
        invite = UserInvite.objects.create(email='a@example.com')
        client.force_login(admin_user)
        response = client.get(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True


# ── register_via_invite view: the public self-service path ─────────────────

@pytest.mark.django_db
class TestRegisterViaInviteView:
    def test_nonexistent_token_404s(self, client):
        response = client.get('/users/invite/11111111-1111-1111-1111-111111111111/')
        assert response.status_code == 404

    def test_expired_invite_renders_expired_page_not_form(self, client):
        invite = UserInvite.objects.create(email='a@example.com')
        invite.expires_at = timezone.now() - datetime.timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert response.status_code == 200
        assert b'No Longer Valid' in response.content

    def test_used_invite_renders_expired_page(self, client):
        invite = UserInvite.objects.create(email='a@example.com', used=True)
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert b'No Longer Valid' in response.content

    def test_valid_get_does_not_require_login(self, client):
        invite = UserInvite.objects.create(email='a@example.com')
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert response.status_code == 200

    def test_valid_post_creates_user_marks_invite_used_and_logs_in(self, client):
        invite = UserInvite.objects.create(email='invitee@example.com')
        response = client.post(reverse('register-invite', kwargs={'token': invite.token}), data={
            'username': 'inviteduser', 'email': 'invitee@example.com',
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        assert response.status_code == 302
        assert response.url == reverse('home')

        user = User.objects.get(username='inviteduser')
        assert hasattr(user, 'profile')

        invite.refresh_from_db()
        assert invite.used is True
        assert invite.used_by == user

        # Auto-login: the session should already be authenticated as the new user.
        session_response = client.get(reverse('profile'))
        assert session_response.status_code == 200

    def test_resubmitting_a_used_invite_does_not_create_a_second_user(self, client):
        invite = UserInvite.objects.create(email='invitee@example.com')
        data = {
            'username': 'onlyonce', 'email': 'invitee@example.com',
            'password1': 'Greatword12', 'password2': 'Greatword12',
        }
        client.post(reverse('register-invite', kwargs={'token': invite.token}), data=data)
        client.logout()

        response = client.post(reverse('register-invite', kwargs={'token': invite.token}), data={
            'username': 'onlyonce_second', 'email': 'invitee@example.com',
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        assert b'No Longer Valid' in response.content
        assert User.objects.filter(username='onlyonce_second').exists() is False
        assert User.objects.filter(username='onlyonce').count() == 1
