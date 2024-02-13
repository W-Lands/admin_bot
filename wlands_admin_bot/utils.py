from pyrogram import filters
from pyrogram.types import Message


def user_filter(*user_ids):
    async def check(flt, __, message: Message) -> bool:
        if message.from_user is None:
            return False
        return message.from_user.id in flt.user_ids

    return filters.create(check, user_ids=user_ids)
