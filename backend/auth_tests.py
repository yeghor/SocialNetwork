import pytest
from authorization.password_manager import hash_password, check_password
from authorization.jwt_manager import JWTService
from databases_manager.redis_manager.redis_manager import RedisService

# """Soluthion:
# https://stackoverflow.com/questions/70015634/how-to-test-async-function-using-pytest
# """
# pytest_plugins = ("pytest_asyncio",)

@pytest.fixture
def prepared_pws() -> tuple[str, str, str]:
    """Indexes: 0 - Correct password | 1 - Wrong password | 2 - Hash of correct password"""
    return ("password", "wrong-password", hash_password("password"))

def test_pw_hashing(prepared_pws):
    assert check_password(prepared_pws[0], prepared_pws[2]) == True
    assert check_password(prepared_pws[1], prepared_pws[2]) == False

@pytest.mark.asyncio
async def test_jwt_and_redis_jwt_saving():
    """Test JWT handling with jwt and redis async library"""

    pass