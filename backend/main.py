from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
from routes import auth_router, social_router
from databases_manager.postgres_manager.models import *
from databases_manager.postgres_manager.database import engine
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.main_managers.social_manager import MainServiceSocial
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as async_redis
import uvicorn
from os import getenv
from dotenv import load_dotenv

load_dotenv()

async def drop_all(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        print("Initialize all postgres models")
        await conn.run_sync(Base.metadata.drop_all)

async def initialize_models(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        print("Drop all postgres models")
        await conn.run_sync(Base.metadata.create_all)

async def drop_redis() -> None:
    client = async_redis.Redis(
        host="localhost",
        port=int(getenv("REDIS_PORT")),
        db=0
    )
    await client.flushall()
    await client.aclose()

async def initialize_data() -> None:
    try:
        session = await get_session()
        async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session, mode="prod") as social_service:
            await social_service.sync_data()

    finally:
        await session.aclose()
# On app startup. https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await drop_all(engine=engine, Base=Base)    
    await initialize_models(engine=engine, Base=Base)
    await drop_redis()
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router.auth)
app.include_router(social_router.social)

# for debug
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)