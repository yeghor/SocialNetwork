from fastapi import HTTPException
from dotenv import load_dotenv
from os import getenv
from functools import wraps

from fastapi import WebSocketDisconnect, WebSocketException, WebSocket, HTTPException
from json.decoder import JSONDecodeError
from pydantic import ValidationError
from sqlalchemy import UnaryExpression



load_dotenv()
Debug = getenv("DEBUG").lower().capitalize().strip()

INTERNAL_SERVER_ERROR_CLIENT_MESSAGE = getenv("INTERNAL_SERVER_ERROR_CLIENT_MESSAGE").strip()

import logging

from exceptions.custom_exceptions import *

def endpoint_exception_handler(func):
    """Use only with asynchronomous code"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if Debug == "False":
            try:
                return await func(*args, **kwargs)
            
            except (BadRequestExc, NotFoundExc, ConflictExc, UnauthorizedExc) as e:
                logging.log(level=logging.WARNING, msg=str(e), exc_info=True)
                raise HTTPException(status_code=e.status_code, detail=e.client_safe_detail)
            
            except InternalServerErrorExc as e:
                logging.log(level=e.logging_type, msg=str(e), exc_info=True)
                raise HTTPException(status_code=e.status_code, detail=e.client_safe_detail)
            
            except Exception as e:
                logging.critical(msg=f"Unexpected exception: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="It's not you, it's us. Something went wrong, please, contact us or try again later")
        elif Debug == "True":
            return await func(*args, **kwargs)
        else:
            raise ValueError("Debug mode invalid value. Check .env file.")

    return wrapper

def web_exceptions_raiser(func):
    """Use only with asynchronomous code"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        
        except (InvalidAction, InvalidFileMimeType, LimitReached, InvalidResourceProvided, ValidationErrorExc, ValidationError) as e:
            if isinstance(e, ValidationError):
                raise BadRequestExc(client_safe_detail="Invalid request data received", dev_log_detail=str(e), exc_type=e)
            
            raise BadRequestExc(client_safe_detail=e.client_safe_detail, dev_log_detail=str(e), exc_type=e) from e
        
        except Unauthorized as e:
            raise UnauthorizedExc(client_safe_detail=e.client_safe_detail, dev_log_detail=str(e), exc_type=e) from e 
        
        except ResourceNotFound as e:
            raise NotFoundExc(client_safe_detail=e.client_safe_detail, dev_log_detail=str(e), exc_type=e) from e
        
        except Collision as e:
            raise ConflictExc(client_safe_detail=e.client_safe_detail, dev_log_detail=str(e), exc_type=e) from e
        
        except (PostgresError, ChromaDBError, RedisError, MediaError, JWTError, BcryptError, WrongDataFound) as e:
            logging_level = 40
            if isinstance(e, MediaError):
                logging_level = 50 # Be aware of cases when postgres database and s3 or local data NOT synced

            raise InternalServerErrorExc(
                client_safe_detail=INTERNAL_SERVER_ERROR_CLIENT_MESSAGE,
                dev_log_detail=str(e),
                exc_type=e
            ) from e
        
        # We must handle these exceptions becasue: in this project, decorated with `web_exception_raiser` functions call functions that also decorated with the decorator.
        # By handling exceptions that being raised in this decorator too we can keep correct exception chaining.
        except (BadRequestExc, UnauthorizedExc, NotFoundExc, ConflictExc, InternalServerErrorExc) as e:
            raise e

    return wrapper


def ws_endpoint_exception_handler(func):
    @wraps(func)
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        if Debug == "False":
            try:
                return await func(websocket, *args, **kwargs)
            
            except ValidationError as e:
                logging.log(level=logging.WARNING, msg="WSEndpointErrorHandler: Websocket handler received invalid ExpectedWSData schema data.", exc_info=e)
                await websocket.close(code=4001, reason="Data does not match excpected schema.")

            except JSONDecodeError as e:
                logging.log(level=logging.WARNING, msg="WSEndpointErrorHandler: Websocket handler received invalid JSON message format.")
                await websocket.close(code=1007, reason="Invalid JSON data received")

            except WSMessageIsTooBig as e:
                logging.log(level=logging.WARNING, msg=str(e), exc_info=True)
                await websocket.close(code=1009, reason=e.client_safe_detail)

            except UnauthorizedExc as e:
                logging.log(level=logging.WARNING, msg=str(e), exc_info=True)
                raise HTTPException(detail=e.client_safe_detail, status_code=e.status_code)
                
            except InvalidAction as e:
                logging.log(level=logging.WARNING, msg=str(e), exc_info=True)
                await websocket.close(code=1008, reason=e.client_safe_detail)

            except UnauthorizedInWebocket as e:
                logging.log(level=logging.WARNING, msg=str(e), exc_info=True)
                await websocket.close(code=3000, reason=e.client_safe_detail)
                
            except ResourceNotFound as e:
                logging.log(level=logging.ERROR, msg=str(e), exc_info=True)
                await websocket.close(code=1011, reason=e.client_safe_detail)

            except (PostgresError, ChromaDBError, RedisError, MediaError, JWTError, BcryptError, WrongDataFound) as e:
                logging.log(level=logging.CRITICAL, msg=str(e), exc_info=True)
                await websocket.close(code=1011, reason=INTERNAL_SERVER_ERROR_CLIENT_MESSAGE)

            except Exception as e:
                logging.log(level=logging.CRITICAL, msg=f"WSEndpointErrorHandler: Uknown Exception occured {str(e)}", exc_info=True)
                await websocket.close(code=1011, reason=INTERNAL_SERVER_ERROR_CLIENT_MESSAGE)

        elif Debug == "True":
            return await func(websocket, *args, **kwargs)

    return wrapper