from wlands_admin_bot.models._utils import Model
from tortoise import fields


class WlUser(Model):
    id: int = fields.BigIntField(pk=True)
