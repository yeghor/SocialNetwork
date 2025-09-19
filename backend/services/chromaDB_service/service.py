from chromadb import AsyncHttpClient, Collection
from chromadb.api.async_api import AsyncClientAPI
from chromadb.errors import ChromaError
from dotenv import load_dotenv
from os import getenv
from typing import List
from functools import wraps
from services.postgres_service import Post, User
from fastapi import HTTPException
from exceptions.custom_exceptions import EmptyPostsError, ChromaDBError

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
            raise ChromaDBError(f"ChromaDB exception occured: {e}") from e
        except Exception as e:
            raise ChromaDBError(f"Uknown exception occured: {e}") from e
    return wrapper

class ChromaService:
    @staticmethod
    def extract_ids_from_metadata(metadatas, page: int, pagination: int) -> List[str]:
        # TODO: !!!!!!!
        all_ids = [str(meta["post_id"]) for batch in metadatas["metadatas"] for meta in batch]
        return all_ids[pagination*page:(pagination*page)+pagination]
        
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
    async def get_n_related_posts_ids(self, user: User, page: int, post_relation: List[Post], pagination: int)-> List[str]:
        """Get n posts related to user's history \n If user history empty - return [] \n `views_history` Must be list of Posts in descending view date."""

        if not post_relation:
            return []
        
        related_posts_metadatas = await self.__collection.query(
            query_texts=[f"{post.title} {post.text} {post.published.strftime(self._datetime_format)}" for post in post_relation],
            n_results=((pagination * page) + pagination + GET_EXTRA_CHROMADB_RELATED_RESULTS),
        )

        return self.extract_ids_from_metadata(metadatas=related_posts_metadatas, page=page, pagination=pagination)
       

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

    # @chromaDB_error_handler
    async def search_posts_by_prompt(self, prompt: str, page: int, n: int) -> List[str]:
        search_result = await self.__collection.query(
            query_texts=[prompt.strip()],
            n_results=((n * page) + n + GET_EXTRA_CHROMADB_RELATED_RESULTS)
        )
        return self.extract_ids_from_metadata(metadatas=search_result, page=page, pagination=n)
    
    @chromaDB_error_handler
    async def delete_by_ids(self, ids: List[str]):
        await self.__collection.delete(
            ids=ids
        )