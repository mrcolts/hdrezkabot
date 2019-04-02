import os


class Config:

    RDB = {
        "host": os.environ.get("RDB_HOST", "rethinkdb"),
        "port": os.environ.get("RDB_PORT", "28015"),
        "db": os.environ.get("RDB_DB", "test")
    }

    DB_TABLES = {
        "serials": "serials",
        "messages": "messages",
        "users": "users",
        "last_update_hash": "last_update_hash"
    }

    BOT = {
        "log_level": "DEBUG",
        "token": os.environ["BOT_TOKEN"]
    }

    PARSERS = {
        "base_url": os.environ.get("HDREZKA_BASE_URL", "http://hdrezka.ag"),
        "serials": {
            "wait_time": 20 * 60,
            "log_level": "DEBUG"
        },
        "updates": {
            "wait_time": 10,
            "log_level": "DEBUG"
        }
    }

    MESSAGE_REFRESH = {
        "sleep_between_refresh": 5,
        "log_level": "DEBUG"
    }
