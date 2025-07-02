from fastapi import FastAPI
import asyncio
from authorization.auth_router import auth
from database.models import *
from database.database import engine
from contextlib import asynccontextmanager


async def initialize_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

# On app startup.https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_models()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth)