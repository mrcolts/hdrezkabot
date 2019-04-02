import os
import logging
import jinja2
import aiohttp_jinja2 as aiojinja
from aiohttp import web

from models.message import Message
from config import Config
from contrib import utils

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MessageView(web.View):

    @aiojinja.template("index.jinja2")
    async def get(self):
        msgs = [msg.cleaned_data async for msg in Message.wrap_raw(Message.manager.all())]

        return {
            "messages": msgs
        }

    def get_recipient_id(self):
        return 182520296

    async def post(self):
        data = await self.request.post()

        await Message(
            recipient=self.get_recipient_id(),
            body=data["text"]
        ).save()
        return web.HTTPFound("/")


app = web.Application()
aiojinja.setup(app, loader=jinja2.FileSystemLoader(os.path.join(BASE_DIR, "templates")))


async def on_startup(app):
    logging.debug("ON startup")
    await Message.init_manager(Config.RDB)


app.on_startup.append(on_startup)
app.add_routes(
    [web.view("/", MessageView)]
)
web.run_app(app, port=8888)
