from fastapi import FastAPI
from authorization.auth_router import auth

app = FastAPI()

app.include_router(auth)