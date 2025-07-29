from uuid import UUID

from wlands_admin_bot.models._utils import Model
from tortoise import fields


class WlUser(Model):
    id: int = fields.BigIntField(pk=True)
    whitelisted: bool = fields.BooleanField(default=True)
    desc: str = fields.CharField(max_length=128, default="")
    wlmc_id: UUID = fields.UUIDField(null=True, default=None)
