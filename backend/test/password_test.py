import pytest
from src.utils.password_validator import validate_password

def test_valid_password():
    assert validate_password("Test@123") == True

def test_password_too_short():
    assert validate_password("Test@1") == False

def test_password_no_special_char():
    assert validate_password("Test1234") == False

def test_password_no_digit():
    assert validate_password("Test@abc") == False

def test_password_no_uppercase():
    assert validate_password("test@123") == False

def test_password_no_lowercase():
    assert validate_password("TEST@123") == False

def test_password_too_long():
    password = "Test@123"+ "a"*122
    assert validate_password(password) == False

def test_password_with_space():
    assert validate_password("Test @123") == False

def test_empty_password():
    assert validate_password("") == False
