from fastapi import Query, HTTPException
from dotenv import load_dotenv
from os import getenv
from typing import Annotated

from exceptions.custom_exceptions import BadRequestExc

load_dotenv()
QUERY_PARAM_MAX_L = int(getenv("QUERY_PARAM_MAX_L"))


def query_prompt_required(prompt: str = Query(..., max_length=QUERY_PARAM_MAX_L)):
    # Somehow... But Depends() makes prompt Query field required...
    if not prompt.strip():
        raise BadRequestExc(dev_log_detail=f"QeryPromptValidator (query_utils): Received empty query prompt.", client_safe_detail=f"Prompt can't be empty")
    return prompt

def page_validator(page: int):
    if not page >= 0:
        raise BadRequestExc(dev_log_detail=f"PageValidator (query_utils): Received page value that is less or equal than 0.", client_safe_detail=f"Invalid page value")
    return int(page)