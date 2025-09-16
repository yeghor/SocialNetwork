from typing import Literal, Type, TypeVar

# Service Layer Exceptions
class EmptyPostsError(Exception):
    """Gets raised in ChromaDB service. Raise if provided post list empty"""

class ServiceLayerBaseBound(Exception):
    """Use in TypeVar"""

class WSInvalidData(Exception):
    """Gets raised when user sent through Websockets invalid `json` data"""


class NoActiveConnectionsOrRoomDoesNotExist(Exception):
    """Gets raised when no active connections on room id or it's not exist"""

    logging_type = 50

E = TypeVar("E", bound=ServiceLayerBaseBound)

# =======
# Endpoint Layer Exceptions 

class EndpointExcConstructor(Exception):
    """Dev log usage: try - except EndpointExcConstructor as e: msg=str(e)"""
    status_code: int

    def __init__(self, client_safe_detail: str, exc_type: Type[E] = Exception, dev_log_detail: str | None = None):
        self.client_safe_detail = client_safe_detail
        self.exc_type = exc_type

        if not dev_log_detail:
            super().__init__(client_safe_detail)
            return
        super().__init__(dev_log_detail) # To pass detail to base exception args - we don't want to break python exception logic

class BadRequestExc(EndpointExcConstructor):
    """Code - 400"""

    status_code: int = 400


class InternalServerErrorExc(EndpointExcConstructor):
    """Code - 500 \n `logging type` - 30 = warning, 40 - error, 50 - critical"""

    status_code: int = 500
    logging_type: Literal[40, 50] = 50


class NotFoundExc(EndpointExcConstructor):
    """Code - 404"""

    status_code: int = 404


class ConflictExc(EndpointExcConstructor):
    """Code - 409"""

    status_code: int = 409

class UnauthorizedExc(EndpointExcConstructor):
    """Code - 401"""

    status_code: int = 401

# ========
# Services layer exceptions 
# These exception that application requires right now, they're growing.

# CLIENT SAFE MESSAGE DOES NOT SPECIFY ANY SPECIFIC ERROR DATA

class ClientSafeServiceError(ServiceLayerBaseBound):
    def __init__(self, detail: str, client_safe_detail: str):
        self.client_safe_detail = client_safe_detail
        super().__init__(detail)


# 404 # PROVIDE DEFIRENT CLIENT SAFE INFO WHERE IT'S NECESSARY
class ResourceNotFound(ClientSafeServiceError):
    """Raise in case provided ID does not exist or similar"""


# 401 PROVIDE SPECIFIED INFO WHEN IT'S SAFE
class Unauthorized(ClientSafeServiceError):
    """Authorization failed? Raise this."""
    
class UnauthorizedInWebocket(ClientSafeServiceError):
    """Raise in websocket and don't re raise HttpException to this."""


# 400 PROVIDE SPECIFIED USER ACTION IN DEV DETAIL (FIRST ARG) AND REGULAR CLIENT ERROR IN `client_safe_detail`
class InvalidAction(ClientSafeServiceError):
    """Raise in case when action can't be done. For examaple - follow user that you already following to. Or follow self"""

class InvalidFileMimeType(ClientSafeServiceError):
    """Raise when provided file mime type invalid"""

class LimitReached(ClientSafeServiceError):
    """Raise whenever user 'action' limit reached. For example - max post images uploaded"""

class InvalidResourceProvided(ClientSafeServiceError):
    """Raise whenever user's content corrupted or does not fits application rules"""

class ValidationErrorExc(ClientSafeServiceError):
    """Raise in cases provided user data does not valid, for example email validation did not get through regular expressions"""

# Only for Websocket case. Don't catch in service layer exception handler
class WSMessageIsTooBig(ClientSafeServiceError):
    pass

# 409  
class Collision(ClientSafeServiceError):
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

class MultipleDataFound(ServiceLayerBaseBound):
    pass


# Service Layer Exceptions
class EmptyPostsError(Exception):
    """Gets raised in ChromaDB service. Raise if provided post list empty"""

class ServiceLayerBaseBound(Exception):
    """Use in TypeVar"""


class WSInvalidData(Exception):
    """Gets raised when user sent through Websockets invalid `json` data"""
    
class NoActiveConnectionsOrRoomDoesNotExist(Exception):
    """Gets raised when no active connections on room id or it's not exist"""

    logging_type = 50
