import asyncio
import logging

import rethinkdb as r
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor, exceptions
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text, hbold, quote_html
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from contrib.logging import create_logger
from config import Config
from models import User, Serial


loop = asyncio.get_event_loop()
loop.run_until_complete(
    asyncio.gather(
        User.init_manager(Config.RDB),
        Serial.init_manager(Config.RDB)
    )
)

log = create_logger("bot")
logging.getLogger("aiogram").setLevel(logging.INFO)

bot = Bot(token=Config.BOT["token"], loop=loop)

# For example use simple MemoryStorage for Dispatcher.
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# States
NAME = "process_name"
VOICE = "process_voice"


@dp.callback_query_handler(state="*", func=lambda x: x.data and x.data.endswith("_search_page"))
async def callback_serials_page(callback_query: types.CallbackQuery):
    log.debug(f"Change page")

    message = callback_query.message
    state = dp.current_state(chat=message.chat.id)
    data = await state.get_data()
    log.debug(f"Change page state: {data}")
    page_number = data.get("page_number")
    search_query = data.get("search_query")
    if not (page_number and search_query):
        return await bot.answer_callback_query(callback_query.id)

    if callback_query.data.startswith("prev"):
        if page_number > 1:
            page_number -= 1
    elif callback_query.data.startswith("next"):
        page_number += 1
    elif callback_query.data.startswith("start"):
        page_number = 1
    else:
        return await bot.answer_callback_query(callback_query.id)

    serials_msg_data = await create_serials_message(search_query, page_number)
    try:
        await callback_query.message.edit_text(**serials_msg_data)
        await bot.answer_callback_query(callback_query.id)
        await state.update_data(page_number=page_number)
    except exceptions.MessageTextIsEmpty:
        await bot.answer_callback_query(callback_query.id, "Последняя страница")


@dp.callback_query_handler(state="*", func=lambda x: x.data and x.data.startswith("/voice_serial_"))
async def choose_serial_and_voice(callback_query):
    message = callback_query.message
    state = dp.current_state(chat=message.chat.id)
    try:
        _, serial_id, voice = callback_query.data.rsplit("_", maxsplit=2)
        serial_id = int(serial_id)
        log.debug(f"Serial id: {serial_id} voice: voice")
    except Exception:
        return await bot.answer_callback_query(callback_query.id, emojize("Что-то пошло не так:pensive:"))
    serial = await Serial.manager.get(serial_id)
    if not serial or serial and voice not in serial.get("voice", []):
        return await bot.answer_callback_query(message.chat.id, emojize("Упс! Сериал или озвучка не найдены:pensive:"))

    msg_text = text(
        hbold(serial["title"]),
        f'({quote_html(serial["origin_title"])})' if serial["origin_title"] else "",
        str(serial["year"]) if serial["year"] else "",
        hbold("\nЗавершён" if serial["finished"] else "")
    )

    await create_subscription(message.chat.id, serial, voice)
    await bot.answer_callback_query(message.chat.id)
    await state.finish()
    return await bot.send_message(
        message.chat.id,
        text(
            "Теперь вы будете получать увидомления о выходе новых серий сериала:",
            msg_text,
            f"В озвучке {hbold(voice)}",
            sep="\n"
        ),
        parse_mode=ParseMode.HTML
    )


async def create_subscription(user_id, serial, voice):
    serial_sub = {
        "id": serial["id"],
        "excluded_voices": [],
        "title": serial["title"]
    }
    await User.manager.execute(
        User.manager.table.filter(
            r.and_(
                r.row["id"] == user_id,
                r.not_(
                    r.row["serials"].default([]).contains(serial_sub)
                )
            )
        ).update({"serials": r.row["serials"].default([]).append(serial_sub)})
    )


@dp.message_handler(state="*", func=lambda msg: msg.text and msg.text.startswith("/delete_"))
async def delete_serial_subs(message):
    serial_id = message.text.split("_")[-1]
    if serial_id:
        res = await User.manager.execute(
            User.manager.table.get(message.from_user.id).update(
                lambda row: {
                    "serials": row["serials"].default([]).filter(lambda x: x["id"] != int(serial_id))
                }
            )
        )
        log.debug(f"Delete {res}")
    return await bot.send_message(
        message.chat.id,
        text("Теперь вы не будете получать увидомления о выходе новых серий сериала"),
        parse_mode=ParseMode.HTML
    )


@dp.message_handler(state="*", func=lambda msg: msg.text and msg.text.startswith("/serial_"))
async def process_serial(message: types.Message):
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    try:
        serial_id = int(message.text.rsplit("_")[-1])
        log.debug(f"Serial id {serial_id}")
    except Exception:
        return await bot.send_message(message.chat.id, emojize("Что-то пошло не так:pensive:"))
    serial = await Serial.manager.get(serial_id)
    if not serial:
        return await bot.send_message(message.chat.id, emojize("Упс! Сериал не найден:pensive:"))

    msg_text = text(
        hbold(serial["title"]),
        f'({quote_html(serial["origin_title"])})' if serial["origin_title"] else "",
        str(serial["year"]) if serial["year"] else "",
        hbold("\nЗавершён" if serial["finished"] else "")
    )

    # if not serial.get("voice"):
    await create_subscription(message.chat.id, serial, None)
    return await bot.send_message(
        message.chat.id,
        text("Теперь вы будете получать увидомления о выходе новых серий сериала:\n", msg_text),
        parse_mode=ParseMode.HTML
    )

    # reply_markup = types.InlineKeyboardMarkup(row_width=1)
    # for voice in serial["voice"]:
    #     reply_markup.add(
    #         types.InlineKeyboardButton(voice, callback_data=f"/voice_serial_{serial['id']}_{voice}")
    #     )
    #
    # reply_markup.add(
    #     types.InlineKeyboardButton("Отмена", callback_data="cancel")
    # )
    #
    # await state.set_state(VOICE)
    #
    # return await bot.send_message(
    #     message.chat.id,
    #     msg_text,
    #     parse_mode=ParseMode.HTML,
    #     reply_markup=reply_markup
    # )


@dp.message_handler(state="*", func=lambda msg: msg.text == "Добавить сериал")
async def add_serial_process(message):
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    await state.set_state(NAME)
    await bot.send_message(
        message.chat.id,
        emojize("Введи название:")
    )


@dp.message_handler(state="*", func=lambda msg: msg.text == "Список сериалов")
async def show_serial_list(message):
    serials = await User.manager.execute(
        User.manager.table.get(message.from_user.id).get_field("serials").default([])
    )
    if not serials:
        return await bot.send_message(message.chat.id, "У вас пока нет сериалов")
    msg = text(*[
        text(
            hbold(serial["title"]), " ",
            # serial["voice"] if serial["voice"] else "",
            "\nУдалить:",
            f"/delete_{serial['id']}\n",
        )
        for serial in serials
    ], sep="\n")
    return await bot.send_message(message.from_user.id, text(hbold("Сериалы:"), "\n\n", msg), parse_mode=ParseMode.HTML)


@dp.message_handler(state="*", commands=['start'])
async def cmd_start(message: types.Message):
    """
    Conversation's entry point
    """
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    await state.set_state(NAME)
    new_user = User(
        **{
            "chat_id": message.chat.id,
            "is_active": True,
            **message.chat.to_python(),
            **message.from_user.to_python()
        }
    )
    res = await new_user.save(insert=True, conflict="update")
    log.debug(f"Save user {res}")
    reply_markup = types.ReplyKeyboardMarkup([["Добавить сериал", "Список сериалов"]], resize_keyboard=True)

    await bot.send_message(
        message.chat.id,
        emojize("Привет! Давай поищем твои любимые сериалы!:smile:\nВведи название:"),
        reply_markup=reply_markup
    )


@dp.message_handler(state=NAME, func=lambda msg: msg.text and not msg.text.startswith("/"))
async def process_name(message: types.Message):
    """
    Process user name
    """
    if len(message.text) < 2:
        return await message.reply(emojize("Слишком мало символов:pensive:\nПопробуй ввести что-то другое:"))

    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    await state.update_data(search_query=message.text, page_number=1)

    data = await state.get_data()
    log.debug(f"State: {data}")

    try:
        serials_msg_data = await create_serials_message(message.text, 1)
        await bot.send_message(
            message.chat.id,
            **serials_msg_data
        )
    except exceptions.MessageTextIsEmpty:
        await bot.send_message(
            message.chat.id,
            emojize("Прости, ничего не нашёл:pensive:\nПопробуй ввести что-то другое:")
        )


async def create_serials_message(search_query, page_number, limit=10):
    res = await Serial.manager.execute(
        Serial.manager.table
        .order_by(r.desc("year"))\
        .filter(
            r.and_(
                r.or_(
                    r.row["year"].default(2019) >= 2017, r.row["finished"] == False),
                    r.row["search_field"].match(search_query.lower())
            )
        )\
        .slice(page_number * limit - limit, page_number * limit + 1)
    )

    log.debug(f"Create serial message page {res}")

    msg = text(*[
        text(
            hbold(serial["title"]),
            f'({quote_html(serial["origin_title"])})' if serial["origin_title"] else "",
            str(serial["year"]) if serial["year"] else "",
            hbold("\nЗавершён" if serial["finished"] else ""),
            f'\n/serial_{serial["id"]}\n'
        )
        for serial in res
    ], sep="\n")

    inline_pagination = types.InlineKeyboardMarkup(row_width=2)

    btn_row = [types.InlineKeyboardButton(">", callback_data="next_search_page")]
    if page_number > 1:
        btn_row.insert(0, types.InlineKeyboardButton("<", callback_data="prev_search_page"))
        inline_pagination.add(types.InlineKeyboardButton("В начало", callback_data="start_search_page"))
    inline_pagination.add(*btn_row)

    return {
        "text": msg,
        "reply_markup": inline_pagination,
        "parse_mode": ParseMode.HTML
    }


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, loop=loop, skip_updates=True, on_shutdown=shutdown)
