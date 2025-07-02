from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from os import getenv    

load_dotenv()


url = f"postgresql+asyncpg://{getenv("DB_USERNAME")}:{getenv("DB_PASSWORD")}@{getenv("DB_HOST")}:{getenv("DB_PORT")}/{getenv("DB_NAME")}"

def define_database_url(mode: str) -> str:
    """ Set mode - "prod" to main database | "test" to test database """
    if mode not in ("prod", "test"):
        raise ValueError("Invalid database mode chosen")
    
    if mode == "prod": return f"postgresql+asyncpg://{getenv("DB_USERNAME")}:{getenv("DB_PASSWORD")}@{getenv("DB_HOST")}:{getenv("DB_PORT")}/{getenv("DB_NAME")}"
    elif mode == "test": return f"postgresql+asyncpg://{getenv("DB_USERNAME_TEST")}:{getenv("DB_PASSWORD_TEST")}@{getenv("DB_HOST_TEST")}:{getenv("DB_PORT_TEST")}/{getenv("DB_NAME_TEST")}"


def create_engine(mode: str = "prod") -> AsyncEngine:
    DATABASE_URL = define_database_url(mode)
    return create_async_engine(
        url=DATABASE_URL,
        echo=True
    )

def create_sessionmaker(engine: AsyncEngine) -> sessionmaker[AsyncSession]:
    return sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine,
        class_=AsyncSession 
    )