from fastapi import Query, HTTPException
from dotenv import load_dotenv
from os import getenv
from typing import Annotated

load_dotenv()
QUERY_PARAM_MAX_L = int(getenv("QUERY_PARAM_MAX_L"))


def query_prompt_required(prompt: str = Query(..., max_length=QUERY_PARAM_MAX_L)):
    # Somehow... But Depends() makes prompt Query field required...
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt can't be empty!")
    return prompt

def query_exclude_required(exclude_viewed: bool = Query(..., description="Exclude viewed post. Set to True if user pressed 'load more' button")):
    if not isinstance(exclude_viewed, bool):
        raise HTTPException(status_code=400, detail="Exclude posts wasn't specified correctly")
    return exclude_viewed