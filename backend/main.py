from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
from routes import auth_router, social_router
from databases_manager.postgres_manager.models import *
from databases_manager.postgres_manager.database import engine, initialize_models, drop_all
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.main_managers.social_manager import MainServiceSocial
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.chromaDB_manager.chroma_manager import EmptyPostsError
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as async_redis
import uvicorn
from os import getenv
from dotenv import load_dotenv
from post_popularity_rate_task.popularity_rate import update_post_rates

from post_popularity_rate_task.popularity_rate import scheduler

load_dotenv()
POST_RATING_EXPIRATION = int(getenv("POST_RATING_EXPIRATION"))

async def drop_redis() -> None:
    client = async_redis.Redis(
        host="localhost",
        port=int(getenv("REDIS_PORT")),
        db=0
    )
    await client.flushall()
    await client.aclose()

async def sync_chroma_postgres_data() -> None:
    try:
        session = await get_session()
        async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session, mode="prod") as social_service:
            await social_service.sync_data()
    except EmptyPostsError:
        pass
    finally:
        await session.aclose()

# On app startup. https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):

    # await drop_all(engine=engine, Base=Base)    
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

# for debug
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)