from models.base import Model


class User(Model):
    table_name = "users"

    fields = {
        "chat_id": Model.REQUIRED_FIELD,
        "first_name":  Model.REQUIRED_FIELD,
        "id": Model.REQUIRED_FIELD,
        "is_active": Model.REQUIRED_FIELD,
        "is_bot": Model.REQUIRED_FIELD,
        "language_code":  Model.REQUIRED_FIELD,
        "last_name":  Model.REQUIRED_FIELD,
        "type":  Model.REQUIRED_FIELD,
        "username":  Model.REQUIRED_FIELD
    }
