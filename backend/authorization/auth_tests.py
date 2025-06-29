import pytest
from password_manager import hash_password, check_password


@pytest.fixture
def prepared_pws() -> tuple:
    """Indexes: 0 - Correct password | 1 - Wrong password | 2 - Hash of correct password"""
    return ("password", "wrongpassword", hash_password("password"))


def test_pw_hashing(prepared_pws):
    assert check_password(prepared_pws[0], prepared_pws[2]) == True
    assert check_password(prepared_pws[1], prepared_pws[2]) == True