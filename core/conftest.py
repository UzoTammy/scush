import pytest
from django.contrib.auth.models import User


@pytest.fixture()
def user_1(db):
    return User.objects.create_user('testuser')

@pytest.fixture
def new_user_factory():
    def create_user_app(username:str, password:str=None, first_name:str='firstname',
                        last_name:str='lastname', email:str="testuser@email.com",
                        is_staff:bool=False, is_superuser:bool=False, is_active:bool=True):
        user = User.objects.create_user(username=username, password=password, first_name=first_name,
                                        last_name=last_name, email=email, is_staff=is_staff,
                                        is_superuser=is_superuser, is_active=is_active)
        return user
    return create_user_app

@pytest.fixture
def new_user(db, new_user_factory):
    return new_user_factory("Firstuser", "firstpass", "Myfirstname")


@pytest.fixture
def new_staff_user(db, new_user_factory):
    return new_user_factory("Firstuser", "firstpass", "Myfirstname", is_staff=True)