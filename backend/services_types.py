from typing import Literal
import enum

# ========

ExcludeType = Literal["search", "feed", "viewed", "reply-list"] # TODO: Change "viewed" to "view"

# ========

ImageType = Literal["post", "user"]


# ========

class ActionType(enum.Enum):
    view = "view"
    like = "like"
    reply = "reply"
    repost = "repost"