from os import environ

API_ID = int(environ["API_ID"])
API_HASH = environ["API_HASH"]
BOT_TOKEN = environ["BOT_TOKEN"]
DATABASE_URL = environ["DATABASE_URL"]
ADMIN_IDS = [int(user_id.strip()) for user_id in environ["ADMIN_IDS"].split(",")]
INTERNAL_AUTH_TOKEN = environ["INTERNAL_AUTH_TOKEN"]
