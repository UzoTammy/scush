# from django.test import TestCase


def test_create_user(new_user):
    
    assert new_user.username == 'Firstuser'
    assert not new_user.is_staff

def test_create_staff_user(new_staff_user):
    
    assert new_staff_user.is_staff
