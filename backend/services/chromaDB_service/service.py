from chromadb import AsyncHttpClient, Collection, QueryResult
from chromadb.api.async_api import AsyncClientAPI
from chromadb.errors import ChromaError
from dotenv import load_dotenv
from os import getenv
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Literal
from functools import wraps
from services.postgres_service import Post, User
from uuid import UUID
from fastapi import HTTPException
from datetime import datetime
from mix_posts_consts import FEED_MAX_POSTS_LOAD, MIX_HISTORY_POSTS_RELATED
from services_exceptions import EmptyPostsError

load_dotenv()

CHROMADB_HOST = getenv("CHROMADB_HOST")
PROD_COLLECTION_NAME = getenv("CHROMADB_PROD_COLLECTION_NAME")
TEST_COLLECTION_NAME = getenv("CHROMADB_TEST_COLLECTION_NAME")
PORT = int(getenv("CHROMADB_PORT"))

DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

HISTORY_POSTS_TO_TAKE_INTO_RELATED = int(getenv("HISTORY_POSTS_TO_TAKE_INTO_RELATED"))

GET_EXTRA_CHROMADB_RELATED_RESULTS = int(getenv("GET_EXTRA_CHROMADB_RELATED_RESULTS"))


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
    @staticmethod
    def extract_ids_from_metadata(result, posts_type: Literal["search", "feed"], exclude_ids: List[str] = []) -> List[str]:
        metadatas = sorted(result["metadatas"][0], key=lambda meta: meta["published"], reverse=True)
        print(len(metadatas))
        post_ids = [str(meta["post_id"]) for meta in metadatas]
        prepared_ids = [id_ for id_ in post_ids if id_ not in exclude_ids]
        print(prepared_ids)
        if posts_type == "feed": return prepared_ids[:MIX_HISTORY_POSTS_RELATED]
        elif posts_type == "search": return prepared_ids[:FEED_MAX_POSTS_LOAD]
 

    def __init__(self, client: AsyncClientAPI, collection: Collection, mode: str):
        """To create class object. Use **async** method connect!"""
        self.__collection: Collection = collection
        self.__client: AsyncClientAPI = client
        self._datetime_format = getenv('DATETIME_BASE_FORMAT')
        self.__mode = mode

    @classmethod
    @chromaDB_error_handler
    async def connect(cls, mode: str = "prod") -> "ChromaService":
        if not mode in ("prod", "test"):
            raise ValueError("Invalid chromaDB database mode")
        
        try:
            client = await AsyncHttpClient(port=PORT, host=CHROMADB_HOST)
        except ChromaError:
            raise HTTPException(status_code=500, detail="Connection to chromaDB failed")

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
            self.__collection = await self.__client.create_collection(name=PROD_COLLECTION_NAME)
        elif self.__mode == "test":
            await self.__client.delete_collection(name=TEST_COLLECTION_NAME)
            self.__collection = await self.__client.create_collection(name=TEST_COLLECTION_NAME)
        

    @chromaDB_error_handler
    async def get_n_related_posts_ids(self, user: User, exclude_ids: List[str], post_relation: List[Post], n: int = FEED_MAX_POSTS_LOAD)-> List[str]:
        """Get n posts related to user's history \n If user history empty - return [] \n `views_history` Must be list of Posts in descending view date."""

        if not post_relation:
            return []

        related_posts = await self.__collection.query(
            query_texts=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in post_relation],
            n_results=(n + len(exclude_ids) + GET_EXTRA_CHROMADB_RELATED_RESULTS),
            where={
                "user_id": {
                    "$ne": user.user_id
                }
            }
        )

        return self.extract_ids_from_metadata(result=related_posts, exclude_ids=exclude_ids, posts_type="feed")

    @chromaDB_error_handler
    async def add_posts_data(self, posts: List[Post]) -> None:
        """
        Add new post embeddings or update existing by post ids \n
        If posts empty - raise EmptyPostsError _(declared in `services_exceptions.py`)_
        """
        filtered_posts = [post for post in posts if not post.is_reply]
        
        if not filtered_posts:
            raise EmptyPostsError("Posts list empty. Nothing to sync")

        # Adding only field that CAN'T be nullable to prevent crash
        await self.__collection.upsert(
            ids=[str(post.post_id) for post in filtered_posts],
            documents=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in filtered_posts],
            metadatas=[{"post_id": str(post.post_id), "published": int(post.published.timestamp()), "user_id": str(post.owner_id)} for post in filtered_posts]
        )

    @chromaDB_error_handler
    async def search_posts_by_prompt(self, prompt: str, exclude_ids: List[str], n: int = FEED_MAX_POSTS_LOAD) -> List[str]:
        if not prompt:
            raise ValueError("Empty search prompt!")
        
        search_result = await self.__collection.query(
            query_texts=[prompt.strip()],
            n_results=(n + len(exclude_ids))
        )
        print(n+len(exclude_ids))
        return self.extract_ids_from_metadata(result=search_result, exclude_ids=exclude_ids, posts_type="search")
    
    @chromaDB_error_handler
    async def delete_by_ids(self, ids: List[str]):
        await self.__collection.delete(
            ids=ids
        )