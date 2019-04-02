import time
import asyncio
import logging
import rethinkdb as r

from models import all_models
from contrib.logging import create_logger
from config import Config

logger = create_logger("rdb_init", logging.INFO)

async def connect():
    while True:
        print("Connection...")
        try:
            rdb_connection = await r.connect(**Config.RDB)
            break
        except r.errors.ReqlDriverError as e:
            print("Connection fail", e)
        time.sleep(0.02)

    db_name = Config.RDB["db"]
    if db_name not in await r.db_list().run(rdb_connection):
        await r.db_create(db_name).run(rdb_connection)

    logger.info("DB inited")

    tables = await r.table_list().run(rdb_connection)

    for model in all_models:
        logger.info(f"Work with {model.table_name}")
        if model.table_name not in tables:
            await r.table_create(model.table_name).run(rdb_connection)
        logger.info(f"Table `{model.table_name}` inited")

        indexes = await r.table(model.table_name).index_list().run(rdb_connection)
        for model_index in model.indexes:
            if model_index not in indexes:
                await r.table(model.table_name).index_create(model_index).run(rdb_connection)
            logger.info(f"index `{model_index}` of `{model.table_name}` inited")
    await rdb_connection.close()
    print("ReDB inited")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(connect())
    except Exception as e:
        logger.exception("ReDB init error!")
    finally:
        loop.close()
