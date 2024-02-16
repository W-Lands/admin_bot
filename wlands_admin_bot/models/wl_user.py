from uuid import UUID

from wlands_admin_bot.models._utils import Model
from tortoise import fields


class WlUser(Model):
    id: int = fields.BigIntField(pk=True)
    description: str = fields.CharField(max_length=128)
    wlmc_id: UUID = fields.UUIDField(null=True, default=True, unique=True)
