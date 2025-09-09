from fastapi import HTTPException
from dotenv import load_dotenv
from os import getenv
from functools import wraps

from fastapi import WebSocketDisconnect, WebSocketException, WebSocket

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
        
        except (InvalidAction, InvalidFileMimeType, LimitReached, InvalidResourceProvided, ValidationError) as e:
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


# def ws_endpoint_exception_handler(func):
#     async def wrapper(websocket: WebSocket, *args, **kwargs):
#         try:
#             return await func(websocket, *args, **kwargs)
#         except Unauthorized as e:
#             raise HTTPException(status_code=401, detail=e.client_safe_detail)

#         except WSInvaliddata as e:
#             logging.log(level=logging.WARNING, msg=e)
#             await websocket.close(code=1008)

#         except WebSocketDisconnect:
#             await websocket.close(code=1000)

#         except NoActiveConnectionsOrRoomDoesNotExist as e:
#             logging.log(level=logging.CRITICAL, msg=e, exc_info=True)
#             await websocket.close(code=1011)

#         except Exception as e:
#             logging.log(level=logging.CRITICAL, msg=e, exc_info=True)
#             await websocket.close(code=1011)
 
#     return wrapper