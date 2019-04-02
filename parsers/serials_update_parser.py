import asyncio

import rethinkdb as r
from bs4 import BeautifulSoup

from models import Message, LastUpdateHash, User
from parsers.base import BaseParser
from contrib.mixins import RethinkConnectionMixin
from contrib.logging import create_logger

r.set_loop_type("asyncio")
log = create_logger("serials_update_parser")


class UpdateSerialParser(RethinkConnectionMixin, BaseParser):
    _hash = None

    def __init__(self, config, loop=asyncio.get_event_loop(), session=None):
        super().__init__(config, loop, session)
        self.base_url = f"{config.PARSERS['base_url']}/"
        self.wait_time = config.PARSERS["updates"]["wait_time"]

    async def fetch_today_updates(self):
        raw_html = await self._bound_fetch(self.base_url)
        if not raw_html:
            return None

        soup = BeautifulSoup(raw_html, "html.parser")

        ul_element = soup.find("ul", class_="b-seriesupdate__block_list")
        updates = []
        for li_element in ul_element.find_all("li"):
            a_element = li_element.find("a")
            _id = self.parse_serial_id(a_element["href"])
            season = li_element.find("span").get_text().replace("(", "").replace(" сезон)", "")
            name = a_element.get_text()
            try:
                episode, voice = li_element.find("span", class_="cell-2").get_text().rsplit(" (", maxsplit=1)
                voice = voice.replace(")", "")
            except ValueError:
                episode = li_element.find("span", class_="cell-2").get_text()
                voice = None
            episode = episode.replace(" серия", "")

            update = {
                "serial_id": _id,
                "name": name,
                "season": season,
                "episode": episode,
                "voice": voice,
                "hash": f"{_id}_{season}_{episode}_{voice}",
            }
            updates.append(update)
        return updates

    async def _fetch_data(self):
        while self.is_run():
            updates = await self.fetch_today_updates()
            log.debug(f"Updates raw {updates}")

            last_update_hash = await self.get_last_update()
            log.debug(f"Last update hash {last_update_hash}")
            if last_update_hash:
                index = [idx for idx, x in enumerate(updates) if x["hash"] == last_update_hash]
                if index:
                    updates = updates[:index[0]]

            log.debug(f"Updates {updates}")
            for update in reversed(updates):
                await self.process_update(update)
                await self.set_last_update(update["hash"])

            log.debug("Wait")
            await asyncio.sleep(self.wait_time)

    @classmethod
    async def process_update(cls, update):
        text_msg = f'Вышла новая серия сериала "{update["name"]}"' \
                    f' {update["season"]} сезон {update["episode"]} серия {update["voice"] or ""}'

        watchers = await cls.get_watchers_ids(update["serial_id"])
        async for user_id in watchers:
            message = Message(
                recipient=user_id,
                body=text_msg
            )
            await message.save()

    @staticmethod
    async def get_watchers_ids(serial_id):
        return User.manager.wrap_raw(
            User.manager.execute(
                User.manager.table.filter(
                    r.row["serials"].contains(
                        lambda serial: serial["id"].eq(serial_id)
                    )
                )["id"]
            )
        )

    @staticmethod
    async def get_last_update():
        try:
            last_update = await LastUpdateHash.manager.get(0)
            if not last_update:
                return None
            return last_update["hash"]
        except r.errors.ReqlNonExistenceError:
            return None

    @staticmethod
    async def set_last_update(hash):
        log.debug(f"Set hash {hash}")
        await LastUpdateHash(hash=hash, id=0).save(insert=True, conflict="update")


if __name__ == "__main__":
    from config import config
    parser = UpdateSerialParser(config)
    parser.fetch_data()
