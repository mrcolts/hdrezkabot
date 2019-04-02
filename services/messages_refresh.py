import threading

import rethinkdb as r

from config import config
from models.message import Message
from contrib.logging import create_logger

log = create_logger("messages_refresh")


class MessagesRefresh:
    def __init__(self, config):
        self.config = config
        self.rdb_connection = r.connect(**config["rdb"])
        self._exit = threading.Event()

    def is_run(self):
        return not self._exit.is_set()

    def sleep_service(self, seconds):
        self._exit.wait(seconds)

    def signal_handler(self, *args, **kwargs):
        log.debug("Signal received")
        self._exit.set()

    def run(self):
        log.info("Start Message refresh")
        while self.is_run():
            res = r.table(self.config["db_tables"]["messages"]).\
                filter(r.row["status"] == Message.READY.value).\
                update({"last_update": r.now()}).\
                run(self.rdb_connection)
            log.debug(f"Refresh res: {res}")
            self.sleep_service(self.config["messages_refresh"]["sleep_between_refresh"])


if __name__ == "__main__":
    MessagesRefresh(config).run()
