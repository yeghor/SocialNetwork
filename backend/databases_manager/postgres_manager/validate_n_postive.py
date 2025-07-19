# Moved it here due to circular import

from functools import wraps

def validate_n_postitive(func):
    @wraps(func)
    async def wrapper(n: int, *args, **kwargs):
        if not isinstance(n, int):
            raise ValueError("Invalid number type")
        if n <= 0:
            raise ValueError("Invalid number of entries")
        return await func(n, *args, **kwargs)
    return wrapper