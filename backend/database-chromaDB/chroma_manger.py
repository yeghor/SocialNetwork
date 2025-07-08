import chromadb
from dotenv import load_dotenv
from os import getenv
from sqlalchemy.ext.asyncio import AsyncSession
load_dotenv()

client = chromadb.HttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")

class chromaService:
    def __init__(self, postgres_session: AsyncSession, mode: str = "prod", ):
        """Change mode to "test" to connect to the test database"""
        if not mode in ("prod", "test"):
            raise ValueError("Invalid chromaDB database mode")
        
        if mode == "prod":
            self.__client = chromadb.HttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")
        elif mode == "test":
            self.__client = chromadb.HttpClient(port=int(getenv("CHROMADB_PORT_TEST")), host="localhost")

        self.__postgres_session = postgres_session
        