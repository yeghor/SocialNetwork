from datetime import datetime
from dotenv import load_dotenv
from os import getenv
from typing import List

from databases_manager.postgres_manager.models import Post, PostActions
from databases_manager.postgres_manager.database_utils import get_session


from sqlalchemy import select, text, and_
from sqlalchemy.orm import selectinload

load_dotenv()
DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

POST_RATING_EXPIRATION = int(getenv("POST_RATING_EXPIRATION"))
POST_RATING_EXPIRATION = datetime.utcfromtimestamp(POST_RATING_EXPIRATION)

POST_ACTIONS = {
    "view": 1,
    "like": 3,
    "reply": 5,
    "repost": 8,
}

async def update_post_rates():
    """Calculates new rate, shitfing out old actions."""
    now = datetime.utcnow()
    

    session = await get_session()
    posts_raw = await session.execute(
        select(Post)
        .where((now - Post.last_updated) > POST_RATING_EXPIRATION)
    )
    posts = posts_raw.scalars().all()

    for post in posts:
        actions_raw = await session.execute(
            select(PostActions)
            .where(and_((now - PostActions.date) > POST_RATING_EXPIRATION), PostActions.post_id == post.post_id)
        )
        actions = actions_raw.scalars().all()
        post.popularity_rate = calculate_new_rate(actions=actions)

    await session.commit()
    await session.aclose()

def calculate_new_rate(actions: List[PostActions]) -> int:
    rate = 0
    for action in actions:
        rate += POST_ACTIONS[action.action.value]
    return rate