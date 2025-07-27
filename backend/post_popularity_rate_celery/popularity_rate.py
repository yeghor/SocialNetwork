from datetime import datetime, timedelta
from dotenv import load_dotenv
from os import getenv
from typing import List
from asgiref.sync import async_to_sync

from databases_manager.postgres_manager.models import Post, PostActions
from databases_manager.postgres_manager.database_utils import get_session


from sqlalchemy import select, text, and_
from sqlalchemy.orm import selectinload
from post_popularity_rate_celery.celery_main import celery_app

load_dotenv()
DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

POST_RATING_EXPIRATION = int(getenv("POST_RATING_EXPIRATION"))
EXPIRATION_INTERVAL = timedelta(seconds=int(getenv("POST_RATING_EXPIRATION")))

POST_ACTIONS = {
    "view": 1,
    "like": 3,
    "reply": 5,
    "repost": 8,
}

# https://stackoverflow.com/questions/39815771/how-to-combine-celery-with-asyncio
@celery_app.task
def sync_update_post_rate_task() -> None:
    async_to_sync(update_post_rates)()

async def update_post_rates() -> None:
    """Calculates new rate, shitfing out old actions."""
    try:
        now = datetime.utcnow()

        session = await get_session()
        posts_raw = await session.execute(
            select(Post)
            .where((now - Post.last_updated) > EXPIRATION_INTERVAL)
        )
        posts = posts_raw.scalars().all()

        for post in posts:
            actions_raw = await session.execute(
                select(PostActions)
                .where(and_((now - PostActions.date) > EXPIRATION_INTERVAL), PostActions.post_id == post.post_id)
            )
            actions = actions_raw.scalars().all()
            post.popularity_rate = calculate_new_rate(actions=actions)

        await session.commit()
        await session.aclose()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.aclose()


def calculate_new_rate(actions: List[PostActions]) -> int:
    rate = 0
    for action in actions:
        rate += POST_ACTIONS[action.action.value]
    return rate

celery_app.conf.beat_schedule = {
    f"update_post_popularity_rate_every_{POST_RATING_EXPIRATION}_seconds": {
        "task": "post_popularity_rate_celery.popularity_rate.sync_update_post_rate_task",
        "schedule": float(POST_RATING_EXPIRATION) 
    }
}