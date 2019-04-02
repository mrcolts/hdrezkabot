import asyncio
import logging

import rethinkdb as r
from bs4 import BeautifulSoup

from parsers.base import BaseParser
from contrib.logging import create_logger
from models.serial import Serial


r.set_loop_type("asyncio")


class SerialsParser(BaseParser):

    def __init__(self, config, loop=asyncio.get_event_loop(), session=None):
        super().__init__(config, loop, session)
        self.wait_time = config.PARSERS["serials"]["wait_time"]
        self.logger = create_logger("serial_parser", config.PARSERS["serials"]["log_level"])

    @staticmethod
    def parse_serial_year(url):
        try:
            year = int(url.rsplit(".", maxsplit=1)[0].rsplit("-", maxsplit=1)[1])
            return year if year >= 1900 else None
        except Exception:
            return None

    async def fetch_serials_by_page(self, page_number):
        page_url = self.base_url.format(
           "" if page_number == 1 else f"page/{page_number}/"
        )
        raw_html = await self._bound_fetch(page_url)
        if raw_html is None:
            return None
        soup = BeautifulSoup(raw_html, "lxml")
        return [x["href"] for x in soup.select("div.b-content__inline_item-link > a")]

    async def fetch_serial_data(self, serial_url):
        id_ = self.parse_serial_id(serial_url)
        year = self.parse_serial_year(serial_url)
        raw_html = await self._bound_fetch(serial_url)
        if raw_html is None:
            return None

        soup = BeautifulSoup(raw_html, "lxml")
        orig_name_tag = soup.find("div", class_="b-post__origtitle")
        title = soup.find("h1", attrs={"itemprop": "name"}).get_text()
        origin_title = orig_name_tag.get_text() if orig_name_tag else None
        search_field = title.lower() + ((" " + origin_title.lower()) if origin_title else "")
        serial = Serial(
            id=id_,
            year=year,
            search_field=search_field,
            title=title,
            origin_title=origin_title,
            voice=[x.get_text() for x in soup.find_all("li", class_="b-translator__item")],
            finished=bool(soup.find("div", class_="b-post__infolast"))
        )
        await serial.save(insert=True, conflict="update")
        return serial

    async def _fetch_data(self):
        futures = []
        while self.is_run():
            page = 1
            while True:
                self.logger.debug(f"Fetch serials from page {page}")
                serials_urls = await self.fetch_serials_by_page(page)
                if not serials_urls:
                    self.logger.debug("No serials on page")
                    break

                for serial_url in serials_urls:
                    futures.append(
                        asyncio.ensure_future(self.fetch_serial_data(serial_url))
                    )

                self.logger.debug(f"Tasks: {len(futures)}")
                page += 1

                if len(futures) > 50:
                    self.logger.debug(f"Wait futures: {len(futures)}")
                    await self.wait_futures(futures)


            await self.wait_futures(futures)
            await asyncio.sleep(self.wait_time)

    @staticmethod
    async def wait_futures(futures):
        await asyncio.gather(*futures)
        futures.clear()
