from fastapi import FastAPI
from authorization.auth_router import auth
import pytest

app = FastAPI()

app.include_router(auth)

print(pytest.__version__)