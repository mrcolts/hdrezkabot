async def rethink_iter(cursor):
    while await cursor.fetch_next():
        item = await cursor.next()
        yield item
