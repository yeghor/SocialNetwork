from chromadb import AsyncHttpClient, Collection
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

def chromaDB_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ChromaError as e:
            raise Exception(f"ChromaDB error: {e}")
        except Exception as e:
            raise Exception(f"Unknown error occured while working with chromaDB: {e}")
    return wrapper

class ChromaService:
    def __init__(self, client: AsyncHttpClient, collection):
        """To create class object. Use **async** method connect!"""
        self.__collection: Collection = collection
        self._datetime_format = getenv('DATETIME_BASE_FORMAT')


    @classmethod
    @chromaDB_error_handler
    async def connect(cls, mode: str = "prod") -> None:
        if not mode in ("prod", "test"):
            raise ValueError("Invalid chromaDB database mode")
        
        client = await AsyncHttpClient(port=int(getenv("CHROMADB_PORT")), host="localhost")
        if mode == "prod":
            collection = await client.get_or_create_collection(name=getenv("CHROMADB_PROD_COLLECTION_NAME"))
        elif mode == "test":
            # In case if test-collection exists. Dropping it
            try:
                await client.delete_collection(name="test-collection")
            except Exception:
                pass
            
            collection = await client.get_or_create_collection(name=getenv("CHROMADB_TEST_COLLECTION_NAME"))
        return cls(client=client, collection=collection)

    @validate_n_postitive
    @chromaDB_error_handler
    async def get_n_related_posts_ids(self, user: User, n: int) -> List[UUID]:
        """Get n posts related to user's history"""
        number_of_last_viewed_posts = int(getenv("HISTORY_POSTS_TO_TAKE_INTO_RELATED"))

        posts = [post_history_obj.post for post_history_obj in user.views_history[:number_of_last_viewed_posts] if not post_history_obj.post.is_reply ]

        related_posts = await self.__collection.query(
            query_texts=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in posts],
            n_results=n
        )

        return [UUID(m["post_id"]) for m in related_posts.metadatas[0]]
        
        
    @chromaDB_error_handler
    async def add_posts_data(self, posts: List[Post]) -> None:
        """Add new posts or update existing by post ids."""
        filtered_posts = [post for post in posts if not post.is_reply]

        # Adding only field that CAN'T be nullable to prevent crash
        await self.__collection.upsert(
            ids=[str(post.post_id) for post in filtered_posts],
            documents=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in filtered_posts],
            metadatas=[{"post_id": str(post.post_id)} for post in filtered_posts]
        )
