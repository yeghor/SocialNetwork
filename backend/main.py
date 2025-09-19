from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine
from routes import auth_router, social_router, media_router
from services.postgres_service import Base
from services.postgres_service import get_engine, initialize_models, drop_all, get_session
from services.core_services.main_services import MainServiceSocial
from services.core_services import MainServiceContextManager
from websockets_chat.chat import chat

from exceptions.custom_exceptions import EmptyPostsError

from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as async_redis
import uvicorn
from os import getenv, mkdir
from dotenv import load_dotenv
from post_popularity_rate_task.popularity_rate import update_post_rates

from post_popularity_rate_task.popularity_rate import scheduler

import logging

logging.basicConfig(
    level=logging.WARN,
    filename="app_logs.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()
POST_RATING_EXPIRATION = int(getenv("POST_RATING_EXPIRATION_SECONDS"))

engine = None

async def drop_redis() -> None:
    client = async_redis.Redis(
        host="localhost",
        port=int(getenv("REDIS_PORT")),
        db=0
    )
    await client.flushall()
    await client.aclose()

# To be deleted
async def sync_chroma_postgres_data() -> None:
    session = await get_session()
    try:
        async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session, mode="prod") as social_service:
            await social_service.sync_postgres_chroma_DEV_METHOD()
    except EmptyPostsError:
        pass
    finally:
        await session.aclose()

# On app startup. https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # await drop_all(engine=engine, Base=Base)    
    global engine
    engine = await get_engine()

    await initialize_models(engine=engine, Base=Base)
    await sync_chroma_postgres_data()
    # await drop_redis()

    try:
        scheduler.add_job(
            update_post_rates,
            "interval",
            seconds=POST_RATING_EXPIRATION
        )
        scheduler.start()
    except Exception as e:
        scheduler.shutdown()
        raise e("Scheduler initializtion failed")
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
app.include_router(media_router.media_router)
app.include_router(chat)

try:
    mkdir("images")
except FileExistsError:
    pass


# for debug
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)