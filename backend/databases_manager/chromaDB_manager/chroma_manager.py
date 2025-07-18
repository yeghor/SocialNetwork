from chromadb import AsyncHttpClient, Collection
from chromadb.api.async_api import AsyncClientAPI
from chromadb.errors import ChromaError
from dotenv import load_dotenv
from os import getenv
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from functools import wraps
from databases_manager.postgres_manager.models import Post, User
from databases_manager.postgres_manager.database_utils import validate_n_postitive
from uuid import UUID

load_dotenv()

PROD_COLLECTION_NAME = getenv("CHROMADB_PROD_COLLECTION_NAME")
TEST_COLLECTION_NAME = getenv("CHROMADB_TEST_COLLECTION_NAME")
PORT = int(getenv("CHROMADB_PORT"))

HISTORY_POSTS_TO_TAKE_INTO_RELATED = int(getenv("HISTORY_POSTS_TO_TAKE_INTO_RELATED"))
N_MAX_RELATED_POSTS_TO_RETURN = int(getenv("N_MAX_RELATED_POSTS_TO_RETURN"))

class EmptyPostsError(Exception):
    pass    

def chromaDB_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except EmptyPostsError:
            pass
        except ChromaError as e:
            raise Exception(f"ChromaDB error: {e}")
        except Exception as e:
            raise Exception(f"Unknown error occured while working with chromaDB: {e}")
    return wrapper

class ChromaService:
    def __init__(self, client: AsyncClientAPI, collection: Collection, mode: str):
        """To create class object. Use **async** method connect!"""
        self.__collection: Collection = collection
        self.__client: AsyncClientAPI = client
        self._datetime_format = getenv('DATETIME_BASE_FORMAT')
        self.__mode = mode

    @classmethod
    @chromaDB_error_handler
    async def connect(cls, mode: str = "prod") -> None:
        if not mode in ("prod", "test"):
            raise ValueError("Invalid chromaDB database mode")
        
        client = await AsyncHttpClient(port=PORT, host="localhost")
        if mode == "prod":
            collection = await client.get_or_create_collection(name=PROD_COLLECTION_NAME)
        elif mode == "test":
            # In case if test-collection exists. Dropping it
            try:
                await client.delete_collection(name=TEST_COLLECTION_NAME)
            except Exception:
                pass
            
            collection = await client.get_or_create_collection(name=TEST_COLLECTION_NAME)

        return cls(client=client, collection=collection, mode=mode)

    @chromaDB_error_handler
    async def drop_all(self):
        """Drops all embeddings."""

        if self.__mode == "prod":
            await self.__client.delete_collection(name=PROD_COLLECTION_NAME)
        elif self.__mode == "test":
            await self.__client.delete_collection(name=PROD_COLLECTION_NAME)
        

    @validate_n_postitive
    @chromaDB_error_handler
    async def get_n_related_posts_ids(self, user: User, n: int = N_MAX_RELATED_POSTS_TO_RETURN) -> List[UUID]:
        """Get n posts related to user's history"""

        posts = [post_history_obj.post for post_history_obj in user.views_history[:HISTORY_POSTS_TO_TAKE_INTO_RELATED] if not post_history_obj.post.is_reply ]

        related_posts = await self.__collection.query(
            query_texts=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in posts],
            n_results=n
        )

        return [UUID(meta["post_id"]) for meta in related_posts.metadatas[0]]
        
        
    @chromaDB_error_handler
    async def add_posts_data(self, posts: List[Post]) -> None:
        """
        Add new post embeddings or update existing by post UUID
        If posts empty - raise EmptyPostsError (declared in this file)
        """
        filtered_posts = [post for post in posts if not post.is_reply]
        
        if not filtered_posts:
            raise EmptyPostsError("Posts list empty. Nothing to sync")

        # Adding only field that CAN'T be nullable to prevent crash
        await self.__collection.upsert(
            ids=[str(post.post_id) for post in filtered_posts],
            documents=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in filtered_posts],
            metadatas=[{"post_id": str(post.post_id)} for post in filtered_posts]
        )
