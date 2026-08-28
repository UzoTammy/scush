import pytest
from django.contrib.auth.models import Group, User


@pytest.fixture
def new_user_factory():
    def create_user(username: str, password: str = None, first_name: str = 'firstname',
                     last_name: str = 'lastname', email: str = 'testuser@email.com',
                     is_staff: bool = False, is_superuser: bool = False, is_active: bool = True):
        return User.objects.create_user(
            username=username, password=password, first_name=first_name,
            last_name=last_name, email=email, is_staff=is_staff,
            is_superuser=is_superuser, is_active=is_active,
        )
    return create_user


@pytest.fixture
def new_user(db, new_user_factory):
    return new_user_factory('Firstuser', 'firstpass')


@pytest.fixture
def user_in_group_factory(db, new_user_factory):
    """Create a user who belongs to the given group (created if it doesn't exist)."""
    def create_user_in_group(name, username=None, **kwargs):
        username = username or f'{name.lower()}_user'
        user = new_user_factory(username, **kwargs)
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
        return user
    return create_user_in_group


@pytest.fixture
def superuser(db, new_user_factory):
    return new_user_factory('super_user', is_superuser=True, is_staff=True)


@pytest.fixture
def balance_tolerance_setting(db):
    from core.models import Setting

    def set_tolerance(value='1'):
        setting, _ = Setting.objects.get_or_create(
            key='balance_tolerance',
            defaults={'label': 'Balance Tolerance', 'category': 'trade', 'value_type': Setting.TYPE_NUMBER},
        )
        setting.text_value = str(value)
        setting.save(update_fields=['text_value'])
        return setting
    return set_tolerance
