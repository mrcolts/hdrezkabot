from models.base import Model


class Serial(Model):
    table_name = "serials"

    fields = {
        "year": Model.REQUIRED_FIELD,
        "search_field": Model.REQUIRED_FIELD,
        "title": Model.REQUIRED_FIELD,
        "origin_title": Model.REQUIRED_FIELD,
        "voice": Model.REQUIRED_FIELD,
        "finished": Model.REQUIRED_FIELD
    }
