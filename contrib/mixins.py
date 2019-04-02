import rethinkdb as r


class RethinkConnectionMixin:
    def __init__(self, config, loop, *args, **kwargs):
        super().__init__(config, loop, *args, **kwargs)

        self.rdb_conn = loop.run_until_complete(
            self._init_db(
                config.RDB
            )
        )

    @staticmethod
    async def _init_db(config):
        return await r.connect(**config)
