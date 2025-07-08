import chromadb
from dotenv import load_dotenv
from os import getenv
from sqlalchemy.ext.asyncio import AsyncSession
from database.database_utils import validate_n_postitive
from uuid import UUID
from typing import List
from database.models import Post, User

load_dotenv()

client = chromadb.HttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")

class chromaService:
    def __init__(self, postgres_session: AsyncSession, mode: str = "prod"):
        """
        Change mode to "test" to connect to the test database \n
        MUST BE handeled postgres session closing by await close() or using context manager
        """
        if not mode in ("prod", "test"):
            raise ValueError("Invalid chromaDB database mode")
        
        if mode == "prod":
            self.__client = chromadb.AsyncHttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")
        elif mode == "test":
            self.__client = chromadb.AsyncHttpClient(port=int(getenv("CHROMADB_PORT_TEST")), host="localhost")

        self.__postgres_session = postgres_session

    @validate_n_postitive
    async def get_n_related_posts(user_id: UUID, n: int) -> List[Post]:
        """Get n posts related to user's history"""

    # async def load_postgres_data():
    #     """Set up chromaDB database using postgres data"""