import asyncio

from config import Config
from parsers import SerialsParser, UpdateSerialParser
from models import Serial, LastUpdateHash, User, init_models

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    init_models(Config.RDB, loop)

    cours = asyncio.gather(
        # SerialsParser(Config).parse(),
        UpdateSerialParser(Config).parse()
    )

    try:
        loop.run_until_complete(cours)
    finally:
        loop.close()
