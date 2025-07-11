from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
from routes.auth_router import auth
from databases_manager.postgres_manager.models import *
from databases_manager.postgres_manager.database import engine
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

async def drop_all(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def initialize_models(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# On app startup. https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("initialing models")
    await initialize_models(engine=engine, Base=Base)
    # await drop_all(engine=engine, Base=Base)
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


app.include_router(auth)
