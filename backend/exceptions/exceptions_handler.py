from fastapi import HTTPException
from dotenv import load_dotenv
from os import getenv

load_dotenv()
Debug = getenv("DEBUG").capitalize().strip()

import logging

from custom_exceptions import *

def endpoint_exception_handler(func: callable):
    """Use only with asynchronomous code"""
    async def wrapper(*args, **kwargs):
        if Debug == "False":
            try:
                return await func(*args, **kwargs)
            
            except (BadRequestExc, NotFoundExc, ConflictExc) as e:
                logging.log(level=logging.WARNING, msg=e, exc_info=e)
                raise HTTPException(status_code=e.status_code, detail=e.detail)
            
            except InternalServerErrorExc as e:
                logging.log(level=e.logging_type, msg=e.detail, exc_info=e)
                raise HTTPException(status_code=e.status_code, detail=e.detail)
            
            except Exception as e:
                logging.critical(msg=f"Unexpected exception: {e}", exc_info=e)
                raise HTTPException(status_code=500, detail="Something went wrong")
        elif Debug == "True":
            return await func(*args, **kwargs)
        else:
            raise ValueError("Debug mode invalid value. Check .env file.")

    return wrapper

def web_exceptions_raiser(func: callable) -> callable:
    """Use only with asynchronomous code"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (InvalidAction, InvalidFileMimeType, LimitReached, InvalidResourceProvided, ValidationError) as e:
            raise BadRequestExc(user_safe_detail=str(e), exc_type=e)
        except Unauthorized as e:
            raise UnauthorizedExc(user_safe_detail="Unauthorized", dev_log_detail=e, exc_type=e)
        except ResourceNotFound as e:
            raise NotFoundExc(user_safe_detail="Not found", dev_log_detail=e, exc_type=e)
        except Collision as e:
            raise ConflictExc(user_safe_detail=str(e), exc_type=e)
        except (PostgresError, ChromaDBError, RedisError, MediaError, JWTError, BcryptError, WrongDataFound) as e:
            logging_level = 50
            if isinstance(e, MediaError):
                logging_level = 40

            raise InternalServerErrorExc(
                user_safe_detail="It's not you, it's us. Something went wrong, email us or try again later.",
                dev_log_detail=e,
                logging_type=logging_level,
                exc_type=e
            )

    return wrapper
