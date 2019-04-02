import rethinkdb as r
from models.base import Model


class Message(Model):

    class Status:
        READY = "READY"
        DONE = "DONE"
        ERROR = "ERROR"

    table_name = "messages"
    fields = {
        "recipient": Model.REQUIRED_FIELD,
        "body": Model.REQUIRED_FIELD,
        "last_update": Model.DEFAULT_VALUE(r.now()),
        "created": Model.DEFAULT_VALUE(r.now()),
        "status":  Model.DEFAULT_VALUE(Status.READY),
        "error": Model.DEFAULT_VALUE("")
    }

    async def save(self, **kwargs):
        self._data["last_update"] = r.now()
        return await super().save(**kwargs)
