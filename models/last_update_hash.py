from models.base import Model


class LastUpdateHash(Model):
    table_name = "last_update_hash"

    fields = {
        "hash": Model.REQUIRED_FIELD
    }
