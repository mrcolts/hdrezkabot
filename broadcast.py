import asyncio

from aiogram import Bot
from aiogram.utils import exceptions
from aiogram.types import ParseMode

from models import Message
from contrib.logging import create_logger
from config import Config


class TelegramBroadcaster:
    """
    Class which get messages
    from rdb and send it to telegram
    """
    def __init__(self, loop, config):
        """
        :param loop: asyncio.EventLoop
        :param config: config data
        """
        self.logger = create_logger("broadcast")
        self.loop = loop
        self.bot = Bot(token=config.BOT["token"], loop=loop)
        self.config = config

    async def _run(self):
        """
        Corountine which start process messages
        :return:
        """
        async for message in Message.wrap_raw(self.messages_feed()):
            if message:
                self.logger.debug(f"New message {message}")
                await self.process_message(message)

    async def process_message(self, message):
        """
        Corountine which process received message
        :param message: dict message
        :return:
        """
        try:
            error_message = await self.send_tlg_message(message.recipient, message.body)
            if error_message:
                message.error = error_message
                message.status = Message.Status.ERROR
            else:
                message.status = Message.Status.DONE
            self.logger.debug(f"Try update message status: {message}")
            await message.save()
        except exceptions.TelegramAPIError:
            self.logger.exception(f"Error on message {message}")

    async def send_tlg_message(self, user_id, text, disable_notification=False):
        """
        Safe messages sender
        :param user_id: recipient id
        :param text: text to send
        :return: error string or None
        """
        try:
            await self.bot.send_message(
                user_id, text, disable_notification=disable_notification, parse_mode=ParseMode.HTML)
        except exceptions.BotBlocked:
            msg = "blocked by user"
        except exceptions.ChatNotFound:
            msg = "invalid user ID. ChatNotFound"
        except exceptions.UserDeactivated:
            msg = "user is deactivated"
        except exceptions.MessageTextIsEmpty:
            msg = "Msg is empty"
        except exceptions.RetryAfter as e:
            self.logger.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
            await asyncio.sleep(e.timeout)
            return await self.send_tlg_message(user_id, text)  # Recursive call TODO: find something better
        else:
            self.logger.info(f"Target [ID:{user_id}]: success")
            return None

        self.logger.error(f"Target [ID:{user_id}]: {msg}")
        return msg

    def messages_feed(self):
        """
        Create rethinkdb changefeed generator
        :return: generator
        """
        return Message.manager.execute(
            Message.manager.table.filter(Message._row["status"] == Message.Status.READY).changes()["new_val"]
        )

    def run(self):
        """
        run _run corountine in asyncio loop
        :return:
        """
        self.logger.info("Start messsage handler")
        try:
            self.loop.run_until_complete(
                asyncio.gather(self._run(), self.refresh())
            )
        finally:
            loop.close()
            self.logger.info("Finish messsage handler")

    async def refresh(self):
        while True:
            res = await Message.manager.execute(
                Message.manager.table.filter(Message._row["status"] == Message.Status.READY).
                    update({"last_update": Message._r.now()})
            )
            await asyncio.sleep(self.config.MESSAGE_REFRESH["sleep_between_refresh"])
            self.logger.debug(f"Refresh messages res: {res}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(Message.init_manager(Config.RDB))
    message_handler = TelegramBroadcaster(loop, Config)
    message_handler.run()
