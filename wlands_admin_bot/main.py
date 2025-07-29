from base64 import b64encode
from io import BytesIO
from pathlib import Path
from uuid import UUID

from aerich import Command
from httpx import AsyncClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.types import Message
from tortoise import Tortoise

from wlands_admin_bot.utils import WaitForMessage
from .config import API_HASH, API_ID, BOT_TOKEN, ADMIN_IDS, INTERNAL_AUTH_TOKEN, DATABASE_URL
from .models.wl_user import WlUser

bot = Client(
    "wlands-admin",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)
wait = WaitForMessage(bot)
HEADERS = {"Authorization": INTERNAL_AUTH_TOKEN}


@bot.on_message(filters.command("whitelist"))
async def whitelist_command(_, message: Message):
    USAGE = "Usage:\n/whitelist [ view | add <id: int> | remove <id: int> | accept <id: int> | reject <id: int> ]"
    if message.from_user.id not in ADMIN_IDS:
        USAGE = "Usage:\n/whitelist [ request ]"

    args = message.text.split(" ")[1:]
    if len(args) == 0 or (args[0] in {"add", "remove", "accept", "reject"} and len(args) < 2):
        return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

    if message.from_user.id not in ADMIN_IDS and args[0] != "request":
        return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

    match args[0]:
        case "view":
            users = await WlUser.all()
            user_ids = "\n".join([f"  - {user.id}" + (f" ({user.desc})" if user.desc else "") for user in users])
            await message.reply_text(f"Users:\n\n{user_ids}")
        case "add" | "accept":
            if not args[1].isdigit():
                return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)
            user_id = int(args[1])
            await WlUser.update_or_create(id=user_id, default={"whitelisted": True})
            await message.reply_text("User added to whitelist!")
            await bot.send_message(user_id, "You were added to whitelist!")
        case "remove" | "reject":
            if not args[1].isdigit():
                return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)
            user_id = int(args[1])
            if (user := await WlUser.get_or_none(id=user_id)) is None:
                return await message.reply_text("User does not exists!")
            await user.delete()
            if user.whitelisted:
                await message.reply_text("User removed from whitelist!")
            else:
                await message.reply_text("User's whitelist request was rejected!")
            await bot.send_message(user_id, "You were removed from whitelist!")
        case "request":
            if message.from_user.id in ADMIN_IDS:
                return await message.reply_text("What is wrong with you?")

            user = await WlUser.get_or_none(id=message.from_user.id)
            if user is not None and user.whitelisted:
                return await message.reply_text("You already added to whitelist!")
            if user is not None and not user.whitelisted:
                return await message.reply_text("You already sent whitelist request!")

            await WlUser.create(id=message.from_user.id, whitelisted=False)
            await message.reply_text("Whitelist request sent!")
            for admin_id in ADMIN_IDS:
                user_info = f"[{message.from_user.first_name}](tg://user?id=message.from_user.id)"
                if message.from_user.username:
                    user_info += f" (@{message.from_user.username})"
                await bot.send_message(
                    admin_id, f"New whitelist request from {user_info}", parse_mode=ParseMode.MARKDOWN,
                )
        case _:
            await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)


@bot.on_message(filters.command("register") & filters.private)
async def register_command(_, message: Message):
    USAGE = "Usage:\n/register <login: string> <password: string>"

    if ((user := await WlUser.get_or_none(id=message.from_user.id)) is None or not user.whitelisted) \
            and message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(" ")[1:]
    if len(args) < 2:
        return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

    data = {
        "login": args[0][:32],
        "password": args[1],
        "email": f"{args[0][:32]}@wlands.pepega",
        "telegram_id": message.from_user.id,
    }

    async with AsyncClient() as client:
        resp = await client.post("http://wlands-api-internal:9080/users/", json=data, headers=HEADERS)
        if resp.status_code == 200:
            await user.update(wlmc_id=resp.json()["id"])
            return await message.reply_text(f"User created! Email: {args[0][:32]}@wlands.pepega")

        if resp.status_code == 400:
            return await message.reply_text(resp.json()["error_message"])

        print(f"{resp.status_code} | {resp.text}")
        return await message.reply_text(f"Failed to create user!")


@bot.on_message(filters.command("user") & filters.user(ADMIN_IDS))
async def user_command(_, message: Message):
    USAGE = ("Usage:\n/user [ "
             "view <id: int> | "
             "change <id: int> <property: \"wlmc_id\" | \"desc\"> <new_value: str> | "
             "ban <id: int> | "
             "unban <id: int> "
             "]")

    args = message.text.split(" ")[1:]
    if len(args) < 2 or (args[0] == "change" and len(args) < 4) or not args[1].isdigit():
        return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

    user_id = int(args[1])
    if (user := await WlUser.get_or_none(id=user_id)) is None:
        return await message.reply_text("User with this is not found!")

    match args[0]:
        case "view":
            await message.reply_text(f"Info about user {user_id}:\n\n"
                                     f"Id: `{user_id}`\n"
                                     f"Whitelisted: `{user.whitelisted}`\n"
                                     f"Description: `{user.desc}`\n"
                                     f"WLMC id: `{user.wlmc_id}`")
        case "change":
            if args[2] not in {"wlmc_id", "desc"}:
                return await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)

            prop = args[2]
            new_value = args[3]
            if prop == "wlmc_id":
                upd = {"wlmc_id": UUID(new_value)}
            else:
                upd = {"desc": new_value}

            await user.update(**upd)

            await message.reply_text("Updated!")
        case "ban" | "unban":
            act = args[0]

            if user.wlmc_id is None:
                return await message.reply(f"No wlmc user is associated with {user.id}")
            async with AsyncClient() as client:
                resp = await client.post(f"http://wlands-api-internal:9080/users/{user.wlmc_id}/{act}", headers=HEADERS)
                if resp.status_code == 204:
                    return await message.reply_text(f"User {act}ned!")

                if resp.status_code == 400:
                    return await message.reply_text(resp.json()["error_message"])
        case _:
            await message.reply_text(USAGE, parse_mode=ParseMode.DISABLED)


@bot.on_message(filters.command("skin"))
async def user_command(_, message: Message):
    if ((user := await WlUser.get_or_none(id=message.from_user.id)) is None or not user.whitelisted) \
            and message.from_user.id not in ADMIN_IDS:
        return
    if user.wlmc_id is None:
        return await message.reply(f"No wlmc user is associated with your telegram account!")
    chat = message.chat

    await message.reply_text("Send new skin (64x64) as file, or send /delete to remove your current skin")
    got_skin = False
    for _ in range(5):
        msg = await wait.wait_for(chat)
        if msg.media != MessageMediaType.DOCUMENT and msg.text.startswith("/cancel"):
            return await msg.reply("Cancelled.")
        if msg.media != MessageMediaType.DOCUMENT and msg.text.startswith("/delete"):
            async with AsyncClient() as client:
                resp = await client.patch(f"http://wlands-api-internal:9080/users/{user.wlmc_id}", json={"skin": ""},
                                          headers=HEADERS)
                if resp.status_code == 200:
                    return await message.reply_text(f"Skin removed!")

                if resp.status_code == 400:
                    return await message.reply_text(resp.json()["error_message"])

                print(f"{resp.status_code} | {resp.text}")
                return await message.reply_text(f"Failed to removed skin!")
        if msg.media != MessageMediaType.DOCUMENT:
            await msg.reply("Send new skin AS FILE (document). To cancel, send /cancel command.")
            continue
        if msg.document.file_size > 64 * 1024:
            await msg.reply("File is too big (maximum size is 64kb)")
            continue
        got_skin = True
        break

    if not got_skin:
        return await message.reply("To change skin, send /skin command again.")

    image: BytesIO = await msg.download(in_memory=True)
    data = {
        "skin": f"data:image/png;base64,{b64encode(image.getvalue()).decode('utf8')}",
    }
    async with AsyncClient() as client:
        resp = await client.patch(f"http://wlands-api-internal:9080/users/{user.wlmc_id}", json=data, headers=HEADERS)
        if resp.status_code == 200:
            return await message.reply_text(f"Skin changed!")

        if resp.status_code == 400:
            return await message.reply_text(resp.json()["error_message"])

        print(f"{resp.status_code} | {resp.text}")
        return await message.reply_text(f"Failed to change skin!")


async def run():
    migrations_dir = Path(DATABASE_URL.split("://")[1]).parent / "migrations"

    command = Command({
        "connections": {"default": DATABASE_URL},
        "apps": {"models": {"models": ["wlands_admin_bot.models", "aerich.models"], "default_connection": "default"}},
    }, location=str(migrations_dir))
    await command.init()
    if Path(migrations_dir).exists():
        await command.migrate()
        await command.upgrade(True)
    else:
        await command.init_db(True)
    await Tortoise.close_connections()

    await Tortoise.init(db_url=DATABASE_URL, modules={"models": ["wlands_admin_bot.models"]}, _create_db=True)
    await Tortoise.generate_schemas(True)

    await bot.start()
    await idle()
    await bot.stop()


if __name__ == "__main__":
    print("Bot running!")
    bot.run(run())
