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
from telebot.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import get_bot_token
from errors import InvalidDWRToken, InvalidTrainRideFilter
from messages import user_messages as msg, get_tickets_message, format_initial_train_status
from models import TrainRideFilter, StationRecord
from scraper import Scraper
from tracker_manager import tracker_manager, TrackedSearch
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
    needs_price_filter = State()
    max_price = State()
    needs_duration_filter = State()
    max_duration_minutes = State()


class CancelStates(StatesGroup):
    """CancelStates defines state for choosing which tracking to cancel."""
    choosing_cancel = State()


class SearchContext(BaseModel):
    """SearchContext is a class that holds the context of the search process."""
    telegram_user_id: int | None = None
    origin: StationRecord | None = None
    destination: StationRecord | None = None
    departure_date: datetime | None = None
    max_departure_time: time | None = None
    return_date: datetime | None = None
    max_return_time: time | None = None
    max_price: float | None = None
    max_duration_minutes: float | None = None


TOKEN = get_bot_token()
state_storage = StateMemoryStorage()  # TODO: Don't use this in production, (idk why, but use redis)
bot = async_telebot.AsyncTeleBot(TOKEN, state_storage=state_storage)
print("Ya estoy corriendo! Corre a Telegram e interactúa conmigo con los comandos /start o /help")


@bot.message_handler(commands=["start"])
async def send_welcome(message: Message, state: StateContext):
    """Sends a welcome message to the user who initiated the conversation."""
    assert message.from_user is not None
    username = message.from_user.first_name
    await bot.send_message(message.chat.id, msg["welcome"].format(username))


@bot.message_handler(commands=["ayuda", "help"])
async def send_help(message: Message):
    """Sends a help message to the user who requested it."""
    await bot.send_message(message.chat.id, msg["help"], parse_mode="Markdown")


@bot.message_handler(commands=["estado"])
async def show_tracking_status(message: Message, state: StateContext):
    """Shows the active search tracking parameters card if a search is running."""
    assert message.from_user is not None
    user_id = message.from_user.id
    user_trackings = tracker_manager.get_user_trackings(user_id)

    if not user_trackings:
        await bot.send_message(
            message.chat.id,
            "ℹ️ *No tienes ningún rastreo activo en este momento.*\n\n"
            "Usa /buscar para iniciar un nuevo rastreo de billetes.",
            parse_mode="Markdown"
        )
        return

    summary_msg = f"📋 *Rastreos activos actualmente ({len(user_trackings)} en curso):*\n\n"
    for search in user_trackings:
        summary_msg += search.get_summary_card() + "\n"

    summary_msg += "🔄 *El bot se encuentra rastreando la disponibilidad en segundo plano...*"
    await bot.send_message(message.chat.id, summary_msg, parse_mode="Markdown")


@bot.message_handler(commands=["cancelar"])
async def cancel_search(message: Message, state: StateContext):
    """Cancels tracking process interactively, always showing current active trackings."""
    assert message.from_user is not None
    user_id = message.from_user.id

    current_state = await state.get()
    if current_state is not None:
        await state.delete()

    user_trackings = tracker_manager.get_user_trackings(user_id)
    if not user_trackings:
        await bot.send_message(message.chat.id, "ℹ️ No tienes ningún rastreo activo para cancelar.")
        return

    await state.set(CancelStates.choosing_cancel)
    options_msg = "🗑️ *¿Qué rastreo deseas cancelar?*\n\n"
    for t in user_trackings:
        options_msg += f"• *Escribe {t.id}* para cancelar Rastreo #{t.id} ({t.origin.name.title()} ➔ {t.destination.name.title()} - {t.departure_date.strftime('%d/%m/%Y %H:%M')})\n"

    options_msg += "\n• *Escribe 0* para cancelar *TODOS* los rastreos activos."
    await bot.send_message(message.chat.id, options_msg, parse_mode="Markdown")


@bot.message_handler(state=CancelStates.choosing_cancel)
async def cancel_choice_get(message: Message, state: StateContext):
    """Processes user choice for cancelling specific tracking."""
    assert message.from_user is not None
    user_id = message.from_user.id
    cleaned = message.text.strip() if message.text else ""

    if not cleaned.isdigit():
        await bot.send_message(message.chat.id, "Por favor, escribe un número válido de la lista (ej. 1) o 0 para cancelar todos.")
        return

    num = int(cleaned)
    await state.delete()

    if num == 0:
        count = tracker_manager.cancel_all_user_trackings(user_id)
        await bot.send_message(message.chat.id, f"✅ Se han cancelado todos los rastreos activos ({count} en total).")
    else:
        search = tracker_manager.get_tracking(num)
        if search and search.user_id == user_id:
            tracker_manager.remove_tracking(num)
            await bot.send_message(
                message.chat.id,
                f"✅ *[Rastreo #{num}]* ({search.origin.name.title()} ➔ {search.destination.name.title()}) cancelado correctamente.",
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(message.chat.id, f"No se encontró ningún rastreo activo con el número #{num}.")


@bot.message_handler(commands=["buscar"])
async def search_tickets(message: Message, state: StateContext):
    """Starts the search process by asking for the origin station."""
    assert message.from_user is not None
    user_id = message.from_user.id

    can_add, reason = tracker_manager.can_add_tracking(user_id)
    if not can_add:
        await bot.send_message(message.chat.id, reason, parse_mode="Markdown")
        return

    current_state = await state.get()

    if current_state is not None:
        await state.delete()

    await state.set(SearchStates.origin)
    async with state.data() as data:  # type: ignore
        data["telegram_user_id"] = user_id
    await bot.send_message(message.chat.id, msg["start"])


def build_station_keyboard(suggestions: list[StationRecord], callback_prefix: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for idx, st in enumerate(suggestions):
        btn_text = f"📍 {st.name.title()}"
        markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"{callback_prefix}:{idx}"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith("st_orig:"))
async def handle_origin_callback(call: CallbackQuery, state: StateContext):
    idx = int(call.data.split(":")[1])
    async with state.data() as data:  # type: ignore
        suggestions = data.get("origin_suggestions", [])
        if 0 <= idx < len(suggestions):
            selected = suggestions[idx]
            await bot.answer_callback_query(call.id, text=f"Seleccionado: {selected.name.title()}")
            await bot.send_message(
                call.message.chat.id,
                msg["station_confirm"].format(selected.name.title()),
            )
            await state.set(SearchStates.destination)
            data["origin"] = selected
            await bot.send_message(call.message.chat.id, msg["destination"])


@bot.callback_query_handler(func=lambda call: call.data.startswith("st_dest:"))
async def handle_dest_callback(call: CallbackQuery, state: StateContext):
    idx = int(call.data.split(":")[1])
    async with state.data() as data:  # type: ignore
        suggestions = data.get("dest_suggestions", [])
        if 0 <= idx < len(suggestions):
            selected = suggestions[idx]
            await bot.answer_callback_query(call.id, text=f"Seleccionado: {selected.name.title()}")
            await bot.send_message(
                call.message.chat.id,
                msg["station_confirm"].format(selected.name.title()),
            )
            await state.set(SearchStates.departure_date)
            data["destination"] = selected
            await bot.send_message(call.message.chat.id, msg["departure_date"])


@bot.message_handler(state=SearchStates.origin)
async def origin_get(message: Message, state: StateContext):
    """Gets the origin station from the user and asks for the destination station."""
    cleaned = message.text.strip() if message.text else ""
    selected_station = None

    if cleaned.isdigit():
        choice = int(cleaned)
        async with state.data() as data:  # type: ignore
            suggestions = data.get("origin_suggestions", [])
            if 1 <= choice <= len(suggestions):
                selected_station = suggestions[choice - 1]

    if not selected_station:
        res = validate_station(message.text)
        if res.is_valid and res.station:
            selected_station = res.station
        else:
            if res.suggestions:
                async with state.data() as data:  # type: ignore
                    data["origin_suggestions"] = res.suggestions
                markup = build_station_keyboard(res.suggestions, "st_orig")
                await bot.send_message(message.chat.id, res.error_message, reply_markup=markup)
            else:
                await bot.send_message(message.chat.id, res.error_message)
            return

    await bot.send_message(
        message.chat.id,
        msg["station_confirm"].format(selected_station.name.title()),
    )
    await state.set(SearchStates.destination)
    async with state.data() as data:  # type: ignore
        data["origin"] = selected_station
    await bot.send_message(message.chat.id, msg["destination"])


@bot.message_handler(state=SearchStates.destination)
async def destination_get(message: Message, state: StateContext):
    """Gets the destination station from the user and asks for the departure date."""
    cleaned = message.text.strip() if message.text else ""
    selected_station = None

    if cleaned.isdigit():
        choice = int(cleaned)
        async with state.data() as data:  # type: ignore
            suggestions = data.get("dest_suggestions", [])
            if 1 <= choice <= len(suggestions):
                selected_station = suggestions[choice - 1]

    if not selected_station:
        res = validate_station(message.text)
        if res.is_valid and res.station:
            selected_station = res.station
        else:
            if res.suggestions:
                async with state.data() as data:  # type: ignore
                    data["dest_suggestions"] = res.suggestions
                markup = build_station_keyboard(res.suggestions, "st_dest")
                await bot.send_message(message.chat.id, res.error_message, reply_markup=markup)
            else:
                await bot.send_message(message.chat.id, res.error_message)
            return

    await bot.send_message(
        message.chat.id,
        msg["station_confirm"].format(selected_station.name.title()),
    )
    await state.set(SearchStates.departure_date)
    async with state.data() as data:  # type: ignore
        data["destination"] = selected_station
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
        async with state.data() as data:  # type: ignore
            data["departure_date"] = departure_datetime.date
        await bot.send_message(message.chat.id, msg["min_departure_time"])


@bot.message_handler(state=SearchStates.min_departure_time)
async def min_departure_time_get(message: Message, state: StateContext):
    """Gets the minimum departure time and asks for the maximum departure time."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.max_departure_time)
        async with state.data() as data:  # type: ignore
            dep_date: datetime = data["departure_date"]
            if parsed.time is not None:
                dep_date = dep_date.replace(hour=parsed.time.hour, minute=parsed.time.minute, second=0)
            else:
                dep_date = dep_date.replace(hour=0, minute=0, second=0)
            data["departure_date"] = dep_date

        await bot.send_message(message.chat.id, msg["max_departure_time"])


@bot.message_handler(state=SearchStates.max_departure_time)
async def max_departure_time_get(message: Message, state: StateContext):
    """Gets the maximum departure time and asks if they need a return ticket."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.needs_return)
        async with state.data() as data:  # type: ignore
            data["max_departure_time"] = parsed.time

        await bot.send_message(message.chat.id, msg["needs_return"])


@bot.message_handler(state=SearchStates.needs_return)
async def return_get(message: Message, state: StateContext):
    """Gets the user's choice about needing a return ticket and asks for the date if needed."""
    choice = parse_yes_no(message.text)
    if choice is True:
        await state.set(SearchStates.return_date)
        await bot.send_message(message.chat.id, msg["return_date"])
    elif choice is False:
        await state.set(SearchStates.needs_price_filter)
        await bot.send_message(message.chat.id, msg["needs_price_filter"])
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
        async with state.data() as data:  # type: ignore
            dep_date: datetime | None = data.get("departure_date")
            if dep_date and return_datetime.date.date() < dep_date.date():
                await bot.send_message(
                    message.chat.id,
                    "⚠️ La fecha de vuelta no puede ser anterior a la fecha de ida. Por favor, introduce una fecha igual o posterior."
                )
                return

        await state.set(SearchStates.min_return_time)
        async with state.data() as data:  # type: ignore
            data["return_date"] = return_datetime.date
        await bot.send_message(message.chat.id, msg["min_return_time"])


@bot.message_handler(state=SearchStates.min_return_time)
async def min_return_time_get(message: Message, state: StateContext):
    """Gets the minimum return time and asks for the maximum return time."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.max_return_time)
        async with state.data() as data:  # type: ignore
            ret_date: datetime = data["return_date"]
            if parsed.time is not None:
                ret_date = ret_date.replace(hour=parsed.time.hour, minute=parsed.time.minute, second=0)
            else:
                ret_date = ret_date.replace(hour=0, minute=0, second=0)
            data["return_date"] = ret_date

        await bot.send_message(message.chat.id, msg["max_return_time"])


@bot.message_handler(state=SearchStates.max_return_time)
async def max_return_time_get(message: Message, state: StateContext):
    """Gets the maximum return time and asks for price filter preference."""
    parsed = validate_time(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.needs_price_filter)
        async with state.data() as data:  # type: ignore
            data["max_return_time"] = parsed.time

        await bot.send_message(message.chat.id, msg["needs_price_filter"])


@bot.message_handler(state=SearchStates.needs_price_filter)
async def needs_price_filter_get(message: Message, state: StateContext):
    """Asks if the user wants to filter by maximum price."""
    choice = parse_yes_no(message.text)
    if choice is True:
        await state.set(SearchStates.max_price)
        await bot.send_message(message.chat.id, msg["max_price"])
    elif choice is False:
        await state.set(SearchStates.needs_duration_filter)
        async with state.data() as data:  # type: ignore
            data["max_price"] = None
        await bot.send_message(message.chat.id, msg["needs_duration_filter"])
    else:
        await bot.send_message(message.chat.id, msg["wrong_choice"])


@bot.message_handler(state=SearchStates.max_price)
async def ask_for_max_price(message: Message, state: StateContext):
    """Gets the maximum price and asks if the user wants to filter by duration."""
    parsed = validate_float(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        await state.set(SearchStates.needs_duration_filter)
        async with state.data() as data:  # type: ignore
            data["max_price"] = None if parsed.number == 0 else parsed.number

        await bot.send_message(message.chat.id, msg["needs_duration_filter"])


@bot.message_handler(state=SearchStates.needs_duration_filter)
async def needs_duration_filter_get(message: Message, state: StateContext):
    """Asks if the user wants to filter by maximum duration."""
    choice = parse_yes_no(message.text)
    if choice is True:
        await state.set(SearchStates.max_duration_minutes)
        await bot.send_message(message.chat.id, msg["max_duration"])
    elif choice is False:
        async with state.data() as data:  # type: ignore
            data["max_duration_minutes"] = None
        await finalize_and_start_tracking(message, state)
    else:
        await bot.send_message(message.chat.id, msg["wrong_choice"])


@bot.message_handler(state=SearchStates.max_duration_minutes)
async def get_max_duration(message: Message, state: StateContext):
    """Gets the maximum duration and starts the tracking process."""
    parsed = validate_float(message.text)

    if not parsed:
        await bot.send_message(message.chat.id, parsed.error_message)
    else:
        async with state.data() as data:  # type: ignore
            data["max_duration_minutes"] = None if parsed.number == 0 else parsed.number

        await finalize_and_start_tracking(message, state)


async def finalize_and_start_tracking(message: Message, state: StateContext):
    """Finalizes search configuration and registers tracking task."""
    assert message.from_user is not None
    user_id = message.from_user.id

    can_add, reason = tracker_manager.can_add_tracking(user_id)
    if not can_add:
        await state.delete()
        await bot.send_message(message.chat.id, reason, parse_mode="Markdown")
        return

    async with state.data() as data:  # type: ignore
        search_obj = TrackedSearch(
            id=0,
            user_id=user_id,
            origin=data["origin"],
            destination=data["destination"],
            departure_date=data["departure_date"],
            max_departure_time=data.get("max_departure_time"),
            return_date=data.get("return_date"),
            max_return_time=data.get("max_return_time"),
            max_price=data.get("max_price"),
            max_duration_minutes=data.get("max_duration_minutes"),
        )

    tracking_id = tracker_manager.add_tracking(search_obj)
    await state.delete()

    summary = (
        f"📋 *Rastreo #{tracking_id} configurado con éxito:*\n"
        f"• *Origen:* {search_obj.origin.name.title()}\n"
        f"• *Destino:* {search_obj.destination.name.title()}\n"
        f"• *Salida:* {search_obj.departure_date.strftime('%d/%m/%Y a las %H:%M')}\n"
        f"• *Hora tope salida:* {search_obj.max_departure_time.strftime('%H:%M') if search_obj.max_departure_time else 'Sin límite'}\n"
    )
    if search_obj.return_date:
        summary += f"• *Vuelta:* {search_obj.return_date.strftime('%d/%m/%Y a las %H:%M')}\n"
        summary += f"• *Hora tope vuelta:* {search_obj.max_return_time.strftime('%H:%M') if search_obj.max_return_time else 'Sin límite'}\n"
    if search_obj.max_price:
        summary += f"• *Precio máx:* {search_obj.max_price} €\n"
    if search_obj.max_duration_minutes:
        summary += f"• *Duración máx:* {search_obj.max_duration_minutes} min\n"

    summary += "\n🔎 *Consultando estado inicial en Renfe...*"
    await bot.send_message(message.chat.id, summary, parse_mode="Markdown")

    task = asyncio.create_task(run_search_loop(search_obj, message.chat.id))
    search_obj.task = task


def format_station_slug(name: str) -> str:
    name = name.strip().lower()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def build_buy_keyboard(origin: StationRecord, destination: StationRecord, dep_date: datetime) -> InlineKeyboardMarkup:
    """Creates inline buttons with prefilled direct link and official Renfe link."""
    markup = InlineKeyboardMarkup()
    orig_slug = format_station_slug(origin.name)
    dest_slug = format_station_slug(destination.name)
    date_str = dep_date.strftime("%d-%m-%Y")

    trainline_url = f"https://www.thetrainline.com/es/search/{orig_slug}/{dest_slug}/{date_str}"
    renfe_url = "https://www.renfe.com/es/es"

    markup.add(InlineKeyboardButton(text=f"⚡ Abrir directo ya rellenado ({origin.name.title()} ➔ {destination.name.title()})", url=trainline_url))
    markup.add(InlineKeyboardButton(text="🚆 Web Oficial Renfe.com (Si estas con un movil te redirige automáticamente a la app)", url=renfe_url))
    return markup


async def run_search_loop(search: TrackedSearch, chat_id: int):
    """Background task loop for a tracked search."""
    departure_done = False
    return_done = search.return_date is None

    scraper = Scraper(search.origin,
                      search.destination,
                      search.departure_date,
                      search.return_date)

    departure_filter = TrainRideFilter(origin=search.origin.name,
                                       destination=search.destination.name,
                                       departure_date=search.departure_date,
                                       max_duration_minutes=search.max_duration_minutes,
                                       max_price=search.max_price,
                                       max_departure_time=search.max_departure_time)

    return_filter = None
    if not return_done:
        return_filter = TrainRideFilter(origin=search.destination.name,
                                        destination=search.origin.name,
                                        departure_date=search.return_date,
                                        max_duration_minutes=search.max_duration_minutes,
                                        max_price=search.max_price,
                                        max_departure_time=search.max_return_time)

    try:
        initial_trains = scraper.get_trainrides()
        matching_dep = departure_filter.get_matching_rides(initial_trains, include_unavailable=True)

        if matching_dep:
            status_msg = format_initial_train_status(matching_dep, search.origin, search.destination)
            await bot.send_message(chat_id, f"📌 *[Rastreo #{search.id}]*\n\n" + status_msg, parse_mode="Markdown")

            available_now = [t for t in matching_dep if t.available]
            if available_now:
                departure_done = True
                await bot.send_message(chat_id,
                                       get_tickets_message(available_now,
                                                           search.origin,
                                                           search.destination),
                                       parse_mode="Markdown",
                                       reply_markup=build_buy_keyboard(search.origin, search.destination, search.departure_date))
            else:
                await bot.send_message(
                    chat_id,
                    f"🔄 *[Rastreo #{search.id}] Rastreando en segundo plano...*\n"
                    "Te avisaré inmediatamente en cuanto se libere una plaza.",
                    parse_mode="Markdown"
                )
        else:
            raise InvalidTrainRideFilter(f"No se encontraron trenes para el Rastreo #{search.id}.")

        if not return_done and return_filter:
            matching_ret = return_filter.get_matching_rides(initial_trains, include_unavailable=True)
            if matching_ret:
                status_ret_msg = format_initial_train_status(matching_ret, search.destination, search.origin)
                await bot.send_message(chat_id, f"📌 *[Rastreo #{search.id} - Vuelta]*\n\n" + status_ret_msg, parse_mode="Markdown")
                available_ret_now = [t for t in matching_ret if t.available]
                if available_ret_now and search.return_date:
                    return_done = True
                    await bot.send_message(chat_id,
                                           get_tickets_message(available_ret_now,
                                                               search.destination,
                                                               search.origin),
                                           parse_mode="Markdown",
                                           reply_markup=build_buy_keyboard(search.destination, search.origin, search.return_date))

        while not departure_done or not return_done:
            await asyncio.sleep(60)
            trains = scraper.get_trainrides()

            if not departure_done:
                departure_trains = departure_filter.filter_rides(trains)
                departure_done = len(departure_trains) > 0
                if departure_done:
                    await bot.send_message(chat_id,
                                           get_tickets_message(departure_trains,
                                                               search.origin,
                                                               search.destination),
                                           parse_mode="Markdown",
                                           reply_markup=build_buy_keyboard(search.origin, search.destination, search.departure_date))
            if not return_done and return_filter:
                return_trains = return_filter.filter_rides(trains)
                return_done = len(return_trains) > 0
                if return_done and search.return_date:
                    await bot.send_message(chat_id,
                                           get_tickets_message(return_trains,
                                                               search.destination,
                                                               search.origin),
                                           parse_mode="Markdown",
                                           reply_markup=build_buy_keyboard(search.destination, search.origin, search.return_date))

        await bot.send_message(
            chat_id,
            f"✅ *[Rastreo #{search.id}] completado y finalizado automáticamente.*",
            parse_mode="Markdown"
        )
        tracker_manager.remove_tracking(search.id)

    except asyncio.CancelledError:
        pass
    except InvalidTrainRideFilter:
        await bot.send_message(chat_id, f"❌ *[Rastreo #{search.id}]* " + msg["invalid_filter"], parse_mode="Markdown")
        tracker_manager.remove_tracking(search.id)
    except InvalidDWRToken:
        await bot.send_message(chat_id, f"❌ *[Rastreo #{search.id}]* " + msg["invalid_dwr_token"], parse_mode="Markdown")
        tracker_manager.remove_tracking(search.id)
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Error en *[Rastreo #{search.id}]*: {str(e)}", parse_mode="Markdown")
        tracker_manager.remove_tracking(search.id)


async def main():
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    bot.setup_middleware(StateMiddleware(bot))
    commands = [
        BotCommand("buscar", "Iniciar un nuevo rastreo de billetes"),
        BotCommand("estado", "Ver todos los rastreos activos"),
        BotCommand("cancelar", "Cancelar rastreos activos"),
        BotCommand("ayuda", "Mostrar comandos disponibles"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception:
        pass
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
