from httpx import AsyncClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from tortoise import Tortoise

from .config import API_HASH, API_ID, BOT_TOKEN, ADMIN_IDS, INTERNAL_AUTH_TOKEN, DATABASE_URL
from .models.wl_user import WlUser

bot = Client(
    "wlands-admin",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


@bot.on_message(filters.command("whitelist") & filters.user(ADMIN_IDS))
async def whitelist_command(_, message: Message):
    USAGE = "Usage:\n/whitelist [ view | add <id: int> | remove <id: int> ]"

    args = message.text.split(" ")[1:]
    if len(args) == 0 or (args[0] in {"add", "remove"} and len(args) < 2):
        return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

    match args[0]:
        case "view":
            user_ids = await WlUser.all().values_list("id", flat=True)
            user_ids = "\n".join([f"  - {user_id}" for user_id in user_ids])
            await message.reply_text(f"Users:\n\n{user_ids}")
        case "add":
            if not args[1].isdigit():
                return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)
            user_id = int(args[1])
            if await WlUser.filter(id=user_id).exists():
                return await message.reply_text("Already exists!")
            await WlUser.create(id=user_id)
            await message.reply_text("Created!")
        case "remove":
            if not args[1].isdigit():
                return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)
            user_id = int(args[1])
            if (user := await WlUser.get_or_none(id=user_id)) is None:
                return await message.reply_text("User does not exists!")
            await user.delete()
            await message.reply_text("Deleted!")
        case _:
            await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)


@bot.on_message(filters.command("register") & filters.private)
async def register_command(_, message: Message):
    USAGE = "Usage:\n/register <login: string> <password: string>"

    if not await WlUser.filter(id=message.from_user.id).exists() and message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(" ")[1:]
    if len(args) < 2:
        return await message.reply_text(USAGE)

    data = {
        "login": args[0][:32],
        "password": args[1],
        "email": f"{args[0][:32]}@wlands.pepega",
        "telegram_id": message.from_user.id,
    }
    headers = {"Authorization": INTERNAL_AUTH_TOKEN}

    async with AsyncClient() as client:
        resp = await client.post("http://wlands-api-internal:9080/users/", json=data, headers=headers)
        if resp.status_code == 200:
            return await message.reply_text(f"User created!")

        if resp.status_code == 400:
            return await message.reply_text(resp.json()["error_message"])

        print(f"{resp.status_code} | {resp.text}")
        return await message.reply_text(f"Failed to create user!")


async def run():
    await Tortoise.init(db_url=DATABASE_URL, modules={"models": ["wlands_admin_bot.models"]}, _create_db=True)
    await Tortoise.generate_schemas(True)

    await bot.start()
    await idle()
    await bot.stop()


if __name__ == "__main__":
    print("Bot running!")
    bot.run(run())
