from os import getenv
from dotenv import load_dotenv


load_dotenv()

FEED_MAX_POSTS_LOAD = int(getenv("FEED_MAX_POSTS_LOAD", 50))
MIX_HISTORY_POSTS_RELATED = int(FEED_MAX_POSTS_LOAD * float(getenv("MIX_HISTORY_POSTS_RELATED", 0.5)))
MIX_FOLLOWING = int(FEED_MAX_POSTS_LOAD * float(getenv("MIX_FOLLOWING_POSTS", 0.3)))
MIX_UNRELEVANT = int(FEED_MAX_POSTS_LOAD * float(getenv("MIX_UNRELEVANT", 0.2)))
