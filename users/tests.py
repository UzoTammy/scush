import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from djmoney.money import Money

from apply.models import Applicant
from staff.models import Employee, Position

from .forms import EmployeeAccountForm, UserInviteForm
from .models import UserInvite


# ── Helpers ───────────────────────────────────────────────────────────────

def make_employee(first='Staffer', last='Test', n=1, status=True):
    """Create an active Employee (with its Applicant) not yet linked to any User."""
    applicant = Applicant.objects.create(
        first_name=first, second_name='', last_name=f'{last}{n}',
        birth_date=datetime.date(1990, 1, 1), gender='MALE', marital_status='SINGLE',
        qualification='BSC', mobile='080-0000-0000', state='Applied',
    )
    position, _ = Position.objects.get_or_create(name='Sales')
    return Employee.objects.create(
        staff=applicant, date_employed=datetime.date(2022, 1, 1), position=position,
        department='Sales', branch='HQ', banker='GTB', account_number=f'00000{n:04d}',
        basic_salary=Money(Decimal('50000.00'), 'NGN'), allowance=Money(Decimal('10000.00'), 'NGN'),
        tax_amount=Money(Decimal('5000.00'), 'NGN'), status=status, is_confirmed=True,
        official_email=f'{first.lower()}{n}@example.com',
    )


@pytest.fixture
def admin_user(db, user_in_group_factory):
    return user_in_group_factory('Administrator', username='reg_admin')


@pytest.fixture
def employee(db):
    return make_employee()


# ── Forms ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize(
    "password, password2, validity",
    [
        ('Greatword12', 'Greatword12', True),
        ('user22', 'user12', False),   # password mismatch
        ('', 'user33', False),         # no first password
        ('user44', '', False),         # no second password
    ]
)
def test_employee_account_form_password_rules(password, password2, validity):
    form = EmployeeAccountForm(data={'password1': password, 'password2': password2})
    assert form.is_valid() is validity


@pytest.mark.django_db
def test_invite_form_excludes_already_registered_employees(new_user_factory, employee):
    other = make_employee(first='Other', n=2)
    already_registered = new_user_factory('already_registered')
    already_registered.profile.staff = other
    already_registered.profile.save(update_fields=['staff'])

    form = UserInviteForm()
    queryset = form.fields['employee'].queryset
    assert employee in queryset
    assert other not in queryset


@pytest.mark.django_db
def test_invite_form_excludes_inactive_employees():
    inactive = make_employee(first='Gone', n=3, status=False)
    form = UserInviteForm()
    assert inactive not in form.fields['employee'].queryset


# ── UserInvite model ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserInviteModel:
    def test_fresh_invite_is_valid(self, employee):
        invite = UserInvite.objects.create(employee=employee)
        assert invite.is_valid() is True

    def test_expired_invite_is_invalid(self, employee):
        invite = UserInvite.objects.create(employee=employee)
        invite.expires_at = timezone.now() - datetime.timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        assert invite.is_valid() is False

    def test_used_invite_is_invalid_even_if_not_expired(self, employee):
        invite = UserInvite.objects.create(employee=employee, used=True)
        assert invite.is_valid() is False

    def test_username_and_email_are_derived_from_employee(self, employee):
        invite = UserInvite.objects.create(employee=employee)
        assert invite.username == f'{employee.staff.first_name}-{str(employee.pk).zfill(2)}'
        assert invite.email == employee.official_email

    def test_email_falls_back_to_applicant_email_when_no_official_email(self):
        employee = make_employee(first='NoOfficial', n=9)
        employee.official_email = None
        employee.staff.email = 'fallback@example.com'
        employee.staff.save(update_fields=['email'])
        employee.save(update_fields=['official_email'])
        invite = UserInvite.objects.create(employee=employee)
        assert invite.email == 'fallback@example.com'


# ── invite_create view: permission gate + creation ──────────────────────

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

    def test_post_creates_invite_tied_to_creator(self, client, admin_user, employee):
        client.force_login(admin_user)
        response = client.post(reverse('user-invite-create'), data={'employee': employee.pk})
        assert response.status_code == 302
        invite = UserInvite.objects.get(employee=employee)
        assert invite.created_by == admin_user
        assert invite.is_valid() is True

    def test_already_registered_employee_not_selectable(self, client, admin_user, employee, new_user):
        new_user.profile.staff = employee
        new_user.profile.save(update_fields=['staff'])
        client.force_login(admin_user)
        response = client.post(reverse('user-invite-create'), data={'employee': employee.pk})
        assert response.status_code == 200
        assert 'employee' in response.context['form'].errors
        assert UserInvite.objects.filter(employee=employee).exists() is False


# ── invite_delete view: admin can retract a link ────────────────────────

@pytest.mark.django_db
class TestInviteDeleteView:
    def test_admin_can_delete_a_pending_invite(self, client, admin_user, employee):
        invite = UserInvite.objects.create(employee=employee)
        client.force_login(admin_user)
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is False

    def test_deleted_invite_link_404s_afterward(self, client, admin_user, employee):
        invite = UserInvite.objects.create(employee=employee)
        token = invite.token
        client.force_login(admin_user)
        client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))

        response = client.get(reverse('register-invite', kwargs={'token': token}))
        assert response.status_code == 404

    def test_deleting_a_used_invite_does_not_touch_the_created_user(self, client, admin_user, employee):
        invite = UserInvite.objects.create(employee=employee)
        client.post(reverse('register-invite', kwargs={'token': invite.token}), data={
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        invite.refresh_from_db()
        expected_username = invite.username
        client.logout()
        client.force_login(admin_user)
        client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert User.objects.filter(username=expected_username).exists() is True

    def test_non_admin_forbidden(self, client, new_user, employee):
        invite = UserInvite.objects.create(employee=employee)
        client.force_login(new_user)
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 403
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True

    def test_anonymous_redirected_to_login(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        response = client.post(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True

    def test_get_does_not_delete(self, client, admin_user, employee):
        """GET is a safe method — only a POST (the confirm-dialog form submit) deletes."""
        invite = UserInvite.objects.create(employee=employee)
        client.force_login(admin_user)
        response = client.get(reverse('user-invite-delete', kwargs={'pk': invite.pk}))
        assert response.status_code == 302
        assert UserInvite.objects.filter(pk=invite.pk).exists() is True


# ── register_via_invite view: the public self-service path ──────────────

@pytest.mark.django_db
class TestRegisterViaInviteView:
    def test_nonexistent_token_404s(self, client):
        response = client.get('/users/invite/11111111-1111-1111-1111-111111111111/')
        assert response.status_code == 404

    def test_expired_invite_renders_expired_page_not_form(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        invite.expires_at = timezone.now() - datetime.timedelta(days=1)
        invite.save(update_fields=['expires_at'])
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert response.status_code == 200
        assert b'No Longer Valid' in response.content

    def test_used_invite_renders_expired_page(self, client, employee):
        invite = UserInvite.objects.create(employee=employee, used=True)
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert b'No Longer Valid' in response.content

    def test_valid_get_does_not_require_login(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert response.status_code == 200

    def test_valid_get_shows_the_derived_username(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        response = client.get(reverse('register-invite', kwargs={'token': invite.token}))
        assert invite.username.encode() in response.content

    def test_valid_post_creates_user_marks_invite_used_and_logs_in(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        response = client.post(reverse('register-invite', kwargs={'token': invite.token}), data={
            'password1': 'Greatword12', 'password2': 'Greatword12',
        })
        assert response.status_code == 302
        assert response.url == reverse('home')

        expected_username = f'{employee.staff.first_name}-{str(employee.pk).zfill(2)}'
        user = User.objects.get(username=expected_username)
        assert user.email == employee.official_email
        assert user.profile.staff == employee

        invite.refresh_from_db()
        assert invite.used is True
        assert invite.used_by == user

        # Auto-login: the session should already be authenticated as the new user.
        session_response = client.get(reverse('profile'))
        assert session_response.status_code == 200

    def test_resubmitting_a_used_invite_does_not_create_a_second_user(self, client, employee):
        invite = UserInvite.objects.create(employee=employee)
        data = {'password1': 'Greatword12', 'password2': 'Greatword12'}
        client.post(reverse('register-invite', kwargs={'token': invite.token}), data=data)
        client.logout()

        response = client.post(reverse('register-invite', kwargs={'token': invite.token}), data=data)
        assert b'No Longer Valid' in response.content
        expected_username = f'{employee.staff.first_name}-{str(employee.pk).zfill(2)}'
        assert User.objects.filter(username=expected_username).count() == 1
