from datetime import datetime, timedelta
from dotenv import load_dotenv
from os import getenv
from typing import List
from asgiref.sync import async_to_sync

from services.postgres_service import *

from sqlalchemy import select, text, and_
from sqlalchemy.orm import selectinload

from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()
DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

VIEW = int(getenv("VIEW", 1))
LIKE = int(getenv("LIKE", 5))
REPLY = int(getenv("REPLY", 5))

POST_ACTIONS = {
    "view": VIEW,
    "like": LIKE,
    "reply": REPLY,
}

POST_RATING_EXPIRATION_SECONDS = int(getenv("POST_RATING_EXPIRATION_SECONDS"))
EXPIRATION_INTERVAL = timedelta(seconds=POST_RATING_EXPIRATION_SECONDS)

scheduler = AsyncIOScheduler()

async def update_post_rates() -> None:
    """Calculates new rate, shitfing out old actions."""
    print("Task started")
    session = await get_session()
    try:
        engine = await get_engine()
        await initialize_models(engine=engine, Base=Base)
        now = datetime.utcnow()

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
            post.last_rate_calculated = now

        await session.commit()
        print("Task finished")
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await engine.dispose()
        await session.aclose()


def calculate_new_rate(actions: List[PostActions]) -> int:
    rate = 0
    for action in actions:
        rate += POST_ACTIONS[action.action.value]
    return rate
