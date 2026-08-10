"""This module contains the main logic of the bot. The search process is a finite state machine."""

import asyncio
import os
from datetime import datetime, time
from typing import Any, Dict

from pydantic import BaseModel
from telebot import async_telebot, asyncio_filters
from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate
from telebot.asyncio_storage import StateMemoryStorage
from telebot.states import State, StatesGroup
from telebot.states.asyncio.context import StateContext
from telebot.states.asyncio.middleware import StateMiddleware
from telebot.types import Message

from config import get_bot_token
from errors import InvalidDWRToken, InvalidTrainRideFilter
from messages import user_messages as msg, get_tickets_message
from models import TrainRideFilter, StationRecord
from scraper import Scraper
from validators import validate_station, validate_date, validate_float, validate_time, parse_yes_no


class SearchStates(StatesGroup):
    """SearchStates is a class that defines the different states for the search process."""
    origin = State()
    destination = State()
    departure_date = State()
    min_departure_time = State()
    max_departure_time = State()
    needs_return = State()
    return_date = State()
    min_return_time = State()
    max_return_time = State()
    max_price = State()
    max_duration_minutes = State()
    searching = State()


class SearchContext(BaseModel):
    """SearchContext is a class that holds the context of the search process."""
    user_id: int
    origin: StationRecord | None = None
    destination: StationRecord | None = None
    departure_date: datetime | None = None
    max_departure_time: time | None = None
    return_date: datetime | None = None
    max_return_time: time | None = None
    max_price: float | None = None
    max_duration_minutes: float | None = None


ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID") or os.getenv("ALLOWED_USER_IDS")


class AuthMiddleware(BaseMiddleware):
    """Middleware to restrict bot usage to allowed user IDs if ALLOWED_USER_ID is set."""
    def __init__(self, bot_instance):
        super().__init__()
        self.bot_instance = bot_instance
        self.update_types = ["message"]

    async def pre_process(self, message: Message, data):
        if message.text and message.text.strip().startswith(("/id", "/myid")):
            return

        if ALLOWED_USER_ID:
            allowed_ids = [uid.strip() for uid in ALLOWED_USER_ID.split(",") if uid.strip()]
            if message.from_user is None or str(message.from_user.id) not in allowed_ids:
                await self.bot_instance.send_message(message.chat.id, msg["unauthorized_user"])
                return CancelUpdate()

    async def post_process(self, message: Message, data, exception):
        pass


TOKEN = get_bot_token()
state_storage = StateMemoryStorage()  # TODO: Don't use this in production, (idk why, but use redis)
bot = async_telebot.AsyncTeleBot(TOKEN, state_storage=state_storage)
bot.setup_middleware(AuthMiddleware(bot))
print("Ya estoy corriendo! Corre a Telegram e interactúa conmigo con los comandos /start o /help")


@bot.message_handler(commands=["id", "myid"])
async def send_user_id(message: Message):
    """Sends the user their Telegram user ID."""
    assert message.from_user is not None
    uid = message.from_user.id
    await bot.send_message(message.chat.id, msg["my_id"].format(uid, uid))


@bot.message_handler(commands=["start"])
async def send_welcome(message: Message, state: StateContext):
    """Sends a welcome message to the user who initiated the conversation."""
    assert message.from_user is not None
    username = message.from_user.first_name
    await bot.send_message(message.chat.id, msg["welcome"].format(username))


@bot.message_handler(commands=["ayuda"])
async def send_help(message: Message):
    """Sends a help message to the user who requested it."""
    await bot.send_message(message.chat.id, msg["help"])


@bot.message_handler(commands=["cancelar"])
async def cancel_search(message: Message, state: StateContext):
    """Cancels the search process and resets the state."""
    current_state = await state.get()
    if current_state is None:
        return
    await state.delete()
    await bot.send_message(message.chat.id, msg["cancel"])


@bot.message_handler(commands=["buscar"])
async def search_tickets(message: Message, state: StateContext):
    """Starts the search process by asking for the origin station."""
    assert message.from_user is not None
    current_state = await state.get()

    if current_state is not None:
        await bot.send_message(message.chat.id, msg["search_already_running"])
        return

    await state.set(SearchStates.origin)
    await state.add_data(user_id=message.from_user.id)
    await bot.send_message(message.chat.id, msg["start"])


@bot.message_handler(state=SearchStates.origin)
async def origin_get(message: Message, state: StateContext):
    """Gets the origin station from the user and asks for the destination station."""
    origin = validate_station(message.text)

    if not origin:
        await bot.send_message(message.chat.id, origin.error_message)
    else:
        assert origin.station is not None
        await bot.send_message(
            message.chat.id,
            msg["station_confirm"].format(origin.station.name.title()),
        )
        await state.set(SearchStates.destination)
        await state.add_data(origin=origin.station)
        await bot.send_message(message.chat.id, msg["destination"])


@bot.message_handler(state=SearchStates.destination)
async def destination_get(message: Message, state: StateContext):
    """Gets the destination station from the user and asks for the departure date."""
    destination = validate_station(message.text)

    if not destination:
        await bot.send_message(message.chat.id, destination.error_message)
    else:
        assert destination.station is not None
        await bot.send_message(
            message.chat.id,
            msg["station_confirm"].format(destination.station.name.title()),
        )
        await state.set(SearchStates.departure_date)
        await state.add_data(destination=destination.station)
        await bot.send_message(message.chat.id, msg["departure_date"])


@bot.message_handler(state=SearchStates.departure_date)
async def departure_date_get(message: Message, state: StateContext):
    """Gets the departure date from the user and asks for the minimum departure time."""
    departure_datetime = validate_date(message.text)

    if not departure_datetime:
        await bot.send_message(message.chat.id, departure_datetime.error_message)
    else:
        assert departure_datetime.date is not None
        await state.set(SearchStates.min_departure_time)
        await state.add_data(departure_date=departure_datetime.date)
        await bot.send_message(message.chat.id, msg["min_departure_time"])


@bot.message_handler(state=SearchStates.min_departure_time)
async def min_departure_time_get(message: Message, state: StateContext):
    """Gets the minimum departure time and asks for the maximum departure time."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        async with state.data() as data:  # type: ignore
            dep_date: datetime = data["departure_date"]
            if parsed.time is not None:
                dep_date = dep_date.replace(hour=parsed.time.hour, minute=parsed.time.minute, second=0)
            else:
                dep_date = dep_date.replace(hour=0, minute=0, second=0)
            await state.add_data(departure_date=dep_date)

        await state.set(SearchStates.max_departure_time)
        await bot.send_message(message.chat.id, msg["max_departure_time"])


@bot.message_handler(state=SearchStates.max_departure_time)
async def max_departure_time_get(message: Message, state: StateContext):
    """Gets the maximum departure time and asks if they need a return ticket."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.needs_return)
        await state.add_data(max_departure_time=parsed.time)
        await bot.send_message(message.chat.id, msg["needs_return"])


@bot.message_handler(state=SearchStates.needs_return)
async def return_get(message: Message, state: StateContext):
    """Gets the user's choice about needing a return ticket and asks for the date if needed."""
    choice = parse_yes_no(message.text)
    if choice is True:
        await state.set(SearchStates.return_date)
        await bot.send_message(message.chat.id, msg["return_date"])
    elif choice is False:
        await state.set(SearchStates.max_price)
        await bot.send_message(message.chat.id, msg["max_price"])
    else:
        await bot.send_message(message.chat.id, msg["wrong_choice"])


@bot.message_handler(state=SearchStates.return_date)
async def return_date_get(message: Message, state: StateContext):
    """Gets the return date from the user and asks for the minimum return time."""
    return_datetime = validate_date(message.text)

    if not return_datetime:
        await bot.send_message(message.chat.id, return_datetime.error_message)
    else:
        assert return_datetime.date is not None
        await state.set(SearchStates.min_return_time)
        await state.add_data(return_date=return_datetime.date)
        await bot.send_message(message.chat.id, msg["min_return_time"])


@bot.message_handler(state=SearchStates.min_return_time)
async def min_return_time_get(message: Message, state: StateContext):
    """Gets the minimum return time and asks for the maximum return time."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        async with state.data() as data:  # type: ignore
            ret_date: datetime = data["return_date"]
            if parsed.time is not None:
                ret_date = ret_date.replace(hour=parsed.time.hour, minute=parsed.time.minute, second=0)
            else:
                ret_date = ret_date.replace(hour=0, minute=0, second=0)
            await state.add_data(return_date=ret_date)

        await state.set(SearchStates.max_return_time)
        await bot.send_message(message.chat.id, msg["max_return_time"])


@bot.message_handler(state=SearchStates.max_return_time)
async def max_return_time_get(message: Message, state: StateContext):
    """Gets the maximum return time and asks for price filter."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.max_price)
        await state.add_data(max_return_time=parsed.time)
        await bot.send_message(message.chat.id, msg["max_price"])


@bot.message_handler(state=SearchStates.max_price)
async def ask_for_max_price(message: Message, state: StateContext):
    """Asks the user for the maximum price and asks for maximum duration."""
    parsed = validate_float(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.max_duration_minutes)
        await state.add_data(max_price=None if parsed.number == 0 else parsed.number)
        await bot.send_message(message.chat.id, msg["max_duration"])


@bot.message_handler(state=SearchStates.max_duration_minutes)
async def get_max_duration(message: Message, state: StateContext):
    """Gets the maximum duration of the trip and starts the search process."""
    parsed = validate_float(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.searching)
        await state.add_data(max_duration_minutes=None if parsed.number == 0 else parsed.number)
        await bot.send_message(message.chat.id, msg["searching"])
        async with state.data() as data:  # type: ignore
            await search_trains(message, state, data)


async def search_trains(message: Message, state: StateContext, ctx: Dict[str, Any]):
    departure_done = False
    return_done = ctx.get("return_date", None) is None

    scraper = Scraper(ctx["origin"],
                      ctx["destination"],
                      ctx["departure_date"],
                      ctx.get("return_date"))

    departure_filter = TrainRideFilter(origin=ctx["origin"].name,
                                       destination=ctx["destination"].name,
                                       departure_date=ctx["departure_date"],
                                       max_duration_minutes=ctx.get("max_duration_minutes"),
                                       max_price=ctx.get("max_price"),
                                       max_departure_time=ctx.get("max_departure_time"))

    if not return_done:
        return_filter = TrainRideFilter(origin=ctx["destination"].name,
                                        destination=ctx["origin"].name,
                                        departure_date=ctx["return_date"],
                                        max_duration_minutes=ctx.get("max_duration_minutes"),
                                        max_price=ctx.get("max_price"),
                                        max_departure_time=ctx.get("max_return_time"))

    try:
        while not departure_done or not return_done:
            trains = scraper.get_trainrides()
            if not departure_done:
                departure_trains = departure_filter.filter_rides(trains)
                departure_done = len(departure_trains) > 0
                if departure_done:
                    await bot.send_message(message.chat.id,
                                           get_tickets_message(departure_trains,
                                                               ctx["origin"],
                                                               ctx["destination"]))
            if not return_done:
                return_trains = return_filter.filter_rides(trains)
                return_done = len(return_trains) > 0
                if return_done:
                    await bot.send_message(message.chat.id,
                                           get_tickets_message(return_trains,
                                                               ctx["destination"],
                                                               ctx["origin"]))
            if not return_done or not departure_done:
                await asyncio.sleep(60)
        await state.delete()

    except InvalidTrainRideFilter:
        await state.delete()
        await bot.send_message(message.chat.id, msg["invalid_filter"])

    except InvalidDWRToken:
        await state.delete()
        await bot.send_message(message.chat.id, msg["invalid_dwr_token"])

    except Exception as e:
        await state.delete()
        await bot.send_message(message.chat.id, msg["undefined_exception"].format(str(e)))

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

if __name__ == "__main__":
    asyncio.run(bot.infinity_polling())
