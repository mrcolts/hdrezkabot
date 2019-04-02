# coding=utf-8
import asyncio

import aiohttp
from aiohttp.client_exceptions import (
    ServerDisconnectedError,
    ClientConnectionError
)

from contrib.logging import create_logger

log = create_logger("base_parser")


class BaseParser:

    def __init__(self, config, loop=asyncio.get_event_loop(), session=None):
        self.base_url = f"{config.PARSERS['base_url']}/series/{{}}"
        self.loop = loop
        self.session = self.get_client_session(session, self.loop)
        self.semaphore = asyncio.Semaphore(100)
        self._run = True

    def is_run(self):
        return self._run

    def shutdown(self):
        self._run = False

    async def after_work(self):
        await self.close_session()

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    @staticmethod
    def get_client_session(session, loop):
        async def _get_client_session():
            return aiohttp.ClientSession()

        if session:
            return session
        return loop.run_until_complete(_get_client_session())

    @staticmethod
    def parse_serial_id(url):
        return int(url.rsplit("/", maxsplit=1)[1].split("-", maxsplit=1)[0])

    @staticmethod
    async def _fetch(url, session, shots):
        while shots:
            try:
                async with session.get(url) as resp:
                    log.debug(f"{resp.status} {url}")
                    if resp.status == 404:
                        return None
                    if resp.status != 200:
                        raise ClientConnectionError
                    return await resp.text()
            except (ServerDisconnectedError, ClientConnectionError) as e:
                log.exception("_fetch error")
                await asyncio.sleep(0.5)
                shots -= 1
        return None

    async def _bound_fetch(self, url, shots=5):
        async with self.semaphore:
            return await self._fetch(url, self.session, shots)

    def fetch_data(self):
        self.loop.run_until_complete(self._fetch_data())
        self.loop.run_until_complete(self.after_work())

    async def parse(self):
        try:
            await self._fetch_data()
        except Exception:
            log.exception(f"Parser exit with error")
        await self.after_work()

    async def _fetch_data(self):
        """
        while self.is_run():
            Do stuff
        :return:
        """
        raise Exception("method not implemented")
