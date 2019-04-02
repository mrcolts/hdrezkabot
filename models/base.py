import time
import asyncio
import logging
import rethinkdb as r

from config import Config


r.set_loop_type("asyncio")


async def rethink_iter(cursor):
    while await cursor.fetch_next():
        item = await cursor.next()
        yield item


class ModelManager:

    def __init__(self, table_name, rdb):
        self.rdb = rdb
        self.table = r.table(table_name)

    def __getattr__(self, attr):
        attribute = self.table.__getattribute__(attr)

        if not attribute:
            return super().__getattribute__(attr)

        def __rdb_run_decorator(*args, **kwargs):
            return attribute(*args, **kwargs).run(self.rdb)

        return __rdb_run_decorator

    async def all(self):
        return await self.table.run(self.rdb)

    async def execute(self, query):
        return await query.run(self.rdb)

    @staticmethod
    async def connect(config):
        return await r.connect(**config)

    @classmethod
    async def create(cls, table_name, rdb_config):
        rdb = await cls.connect(rdb_config)
        return cls(table_name, rdb)

    @classmethod
    async def wrap_raw(cls, async_cursor):
        async for raw in rethink_iter(await async_cursor):
            yield raw


class Model:
    REQUIRED_FIELD = (False, None)
    DEFAULT_VALUE = lambda value: (True, value)

    class Exceptions:
        class ManagerDoesNotInitializated(BaseException):
            pass

        class ValidationError(BaseException):
            pass

        class FieldMissed(ValidationError):
            pass

    table_name = None
    manager = None
    fields = None
    indexes = tuple()
    manager_class = ModelManager

    _row = r.row
    _r = r

    def __init__(self, *args, **kwargs):
        self._data = {}
        self.id = kwargs.pop("id", None)

        if self.manager is None:
            if not "__manager__" in kwargs:
                raise self.Exceptions.ManagerDoesNotInitializated("db manager is None")
            else:
                self.manager = kwargs.pop("__manager__")

        if args:
            self._data = {key: value for key, value in zip(self.fields, args)}

        if kwargs:
            self._data = {
                **self._data,
                **kwargs
            }

    @property
    def cleaned_data(self):
        self.validate()
        if self.id is not None:
            return {"id": self.id, **self._data}
        return self._data

    def validate(self):
        data = {}
        for field_name, field_data in self.fields.items():
            has_default, default_value = field_data
            if field_name in self._data:
                data[field_name] = self._data[field_name]
            elif has_default:
                data[field_name] = default_value
            else:
                raise self.Exceptions.FieldMissed(f"Provide `{field_name}` field name")
        self._data = data

    def __setattr__(self, attr, value):
        if attr in self.fields:
            self._data[attr] = value
        else:
            super().__setattr__(attr, value)

    def __getattr__(self, attr):
        if attr in self.fields:
            return self._data[attr]
        return super().__getattribute__(attr)

    async def save(self, **kwargs):
        """
        :param kwargs: rdb `command` kwargs
        :return:
        """
        insert = kwargs.pop("insert", False)
        if not insert:
            if self.id:
                return await self.manager.update(self.cleaned_data, **kwargs)

        res = await self.manager.insert(self.cleaned_data, **kwargs)
        if self.id is None:
            self.id = res["generated_keys"][0]
        return res

    @classmethod
    async def wrap_raw(cls, async_cursor):
        async for raw in rethink_iter(await async_cursor):
            if raw is None:
                yield None
                continue

            yield cls(**raw)

    @classmethod
    async def init_manager(cls, db_config):
        if cls.manager:
            await cls.manager.server()
        cls.manager = await cls.manager_class.create(cls.table_name, db_config)

    def __str__(self):
        return f"<{type(self).__name__} ({self.id}): {','.join(f'{k}={v}' for k, v in self._data.items())}>"


if __name__ == "__main__":
    config = {
        "host": "0.0.0.0",
        "port": "28015",
        "db": "test"
    }

    async def main(loop):
        Model.fields = {"data": Model.DEFAULT_VALUE(-1)}
        Model.table_name = "x"

        await Model.init_manager(config)

        async for m in Model.wrap_raw(Model.manager.all()):
            print(m)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
