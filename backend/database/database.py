from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
from os import getenv

load_dotenv()


url = f"postgresql+asyncpg://{getenv("DB_USERNAME")}:{getenv("DB_PASSWORD")}@{getenv("DB_HOST")}:{getenv("DB_PORT")}/{getenv("DB_NAME")}"

engine = create_async_engine(
    url=url,
    echo=True # To see database logs
)

session: AsyncSession = async_sessionmaker()

