from fastapi import FastAPI
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from authorization.auth_router import auth
from database.models import *
from database.database import create_engine, create_sessionmaker
from contextlib import asynccontextmanager

engine = create_engine(mode="prod")
SessionLocal = create_sessionmaker(engine)

async def drop_all(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def initialize_models(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# On app startup. https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_models(engine=engine, Base=Base)
    await drop_all(engine=engine, Base=Base)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth)