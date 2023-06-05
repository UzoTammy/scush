import pytest
from .forms import UserRegisterForm

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

@pytest.mark.parametrize(
    "username, email, password, password2, validity", 
    [
        ('user1', 'user1@email.com', 'Greatword12', 'Greatword12', 200),
        # ('user2', 'user2@email.com', 'user22', 'user12', 400), # password mismatch
        # ('user3', 'user3@email.com', '', 'user33', 400), #no first password
        # ('user4', 'user4@email.com', 'user44', '', 400), #no second password
        # ('user1', 'user1emailcom', 'Greatword12', 'Greatword12', 400), # Invalid email
    ]
)
@pytest.mark.django_db
def test_register_view(client, username, email, password, password2, validity):
    response = client.post('register/', 
        data = {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password2
        }
    )
    assert response.status_code == validity