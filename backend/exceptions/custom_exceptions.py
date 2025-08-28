from typing import Literal, Type, TypeVar

E = TypeVar(name="E", bound="ServiceLayerBaseBound")

# Service Layer Exceptions
class EmptyPostsError(Exception):
    """Gets raised in ChromaDB service. Raise if provided post list empty"""

# =======
# Endpoint Layer Exceptions 

class EndpointExcConstructor(Exception):
    status_code: int

    def __init__(self, user_safe_detail: str, exc_type: Type[E], dev_log_detail: str | None = None):
        self.detail = user_safe_detail
        self.exc_type = exc_type

        if not dev_log_detail:
            super().__init__(user_safe_detail)
            return
        super().__init__(dev_log_detail) # To pass detail to base exception args - we don't want to break python exception logic

class BadRequestExc(EndpointExcConstructor):
    """Code - 400"""

    status_code: int = 400


class InternalServerErrorExc(EndpointExcConstructor):
    """Code - 500 \n `logging type` - 30 = warning, 40 - error, 50 - critical"""

    status_code: int = 500
    logging_type: Literal[30, 40, 50] = 50


class NotFoundExc(EndpointExcConstructor):
    """Code - 404"""

    status_code: int = 404


class ConflictExc(EndpointExcConstructor):
    """Core - 409"""

    status_code: int = 409

class UnauthorizedExc(EndpointExcConstructor):
    """Code - 401"""

    status_code: int = 401

# ========
# Services layer exceptions 
# These exception that application requires right now, they're growing.

# 404 

class ServiceLayerBaseBound(Exception):
    """Use in TypeVar"""

class ResourceNotFound(ServiceLayerBaseBound):
    """Raise in case provided ID does not exist or similar"""


# 401
class Unauthorized(ServiceLayerBaseBound):
    """Authorization failed? Raise this"""


# 400 PROVIDE ONLY USER SAFE (FRONTEND) ERROR DATA 
class InvalidAction(ServiceLayerBaseBound):
    """Raise in case when aaction can't be done. For examaple - follow user that you already following to. Or follow self"""

class InvalidFileMimeType(ServiceLayerBaseBound):
    """Raise when provided file mime type invalid"""

class LimitReached(ServiceLayerBaseBound):
    """Raise whenever user 'action' limit reached. For example - max post images uploaded"""

class InvalidResourceProvided(ServiceLayerBaseBound):
    """Raise whenever user's content corrupted or does not fits application rules"""

class ValidationError(ServiceLayerBaseBound):
    """Raise in cases provided user data does not valid, for example email validation through regular expressions"""

# 409 # PROVIDE ONLY USER SAFE (FRONTEND) ERROR DATA 
class Collision(ServiceLayerBaseBound):
    """Raise when something is already exists"""


# 500 DANGER ZONE :)
class PostgresError(ServiceLayerBaseBound):
    pass

class ChromaDBError(ServiceLayerBaseBound):
    pass

class RedisError(ServiceLayerBaseBound):
    pass

class MediaError(ServiceLayerBaseBound):
    """Raise in Image storage if problem on server side"""

class JWTError(ServiceLayerBaseBound):
    pass

class BcryptError(ServiceLayerBaseBound):
    pass

class WrongDataFound(ServiceLayerBaseBound):
    """Raise when unexpected data found. Note method and service where issue occured."""
