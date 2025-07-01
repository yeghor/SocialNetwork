import pytest
from authorization.password_manager import hash_password, check_password
from authorization.jwt_manager import generate_save_token, extract_jwt_payload
from redis_manager import RedisService

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

    user_id = "TEST_ID_12345"
    redis = RedisService(db_pool="test")

    jwt_token = await generate_save_token(user_id, redis) # Tests redis save_jwt() method
    assert await redis.check_jwt_existense(jwt_token)

    payload = extract_jwt_payload(jwt_token)
    assert payload.user_id == user_id

    expiry = await redis.get_jwt_time_to_expiry(jwt_token)
    assert isinstance(expiry, int)

    await redis.delete_jwt(jwt_token)

    assert not await redis.check_jwt_existense(jwt_token)

    expiry = await redis.get_jwt_time_to_expiry(jwt_token)
    assert not expiry