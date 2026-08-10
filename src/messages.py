"""This module contains the messages that the bot sends to the user"""

from typing import List

from models import TrainRideRecord, StationRecord

user_messages = {
    "welcome": "Hola {}. Bienvenido a tu bot de Renfe. Te ayudaré a encontrar billetes de tren para tus viajes. Para empezar, escribe /ayuda para ver los comandos disponibles.",
    "help": "/ayuda - Muestra los comandos disponibles\n/buscar - Busca billetes de tren\n/cancelar - Cancela la búsqueda en curso.",
    "cancel": "La búsqueda ha sido cancelada.",
    "cancel_params": "Reiniciando el proceso de búsqueda, usa /buscar para empezar de nuevo",
    "search_already_running": "Ya hay una búsqueda en curso, por favor espera o utiliza /cancelar para cancelarla",
    "start": "🚉 ¿Desde qué estación sales? (Ejemplo: Vigo, Madrid, Barcelona)",
    "destination": "🚉 ¿A qué estación vas? (Ejemplo: A Coruña, Sevilla, Valencia)",
    "station_invalid": "Por favor, introduce el nombre de una estación válida.",
    "station_confirm": "✅ Estación seleccionada: {}",
    "departure_date": "📅 ¿Qué día es tu viaje de ida? (Ejemplo: 11/08/2026)",
    "min_departure_time": "🕒 ¿A partir de qué hora buscas tren de ida? (Ejemplo: 11:30, o responde 0 para buscar desde las 00:00)",
    "max_departure_time": "🕒 ¿Hasta qué hora como máximo debe salir el tren de ida? (Ejemplo: 11:35, o responde 0 para sin límite de hora)",
    "needs_return": "🔙 ¿Necesitas billete de vuelta? (Responde Sí o No)",
    "return_date": "📅 ¿Qué día es tu viaje de vuelta? (Ejemplo: 15/08/2026)",
    "min_return_time": "🕒 ¿A partir de qué hora buscas tren de vuelta? (Ejemplo: 18:00, o responde 0 para buscar desde las 00:00)",
    "max_return_time": "🕒 ¿Hasta qué hora como máximo debe salir el tren de vuelta? (Ejemplo: 18:30, o responde 0 para sin límite de hora)",
    "max_price": "💵 ¿Quieres filtrar por precio máximo en €? (Ejemplo: 25, o responde 0 si no quieres filtrar por precio)",
    "max_duration": "⏳ ¿Quieres filtrar por duración máxima en minutos? (Ejemplo: 90, o responde 0 si no quieres filtrar por duración)",
    "searching": "🔎 Guardado. Iniciando búsqueda y rastreo de billetes...",
    "station_not_found": "No encontré la estación exacta para '{}'. ¿Te refieres a alguna de estas?\n\n{}\n\nPor favor, escribe el nombre de nuevo.",
    "confirm_date": "Vale, fecha registrada: {}",
    "wrong_date": "Perdona, no he entendido la fecha, por favor introdúcela en formato DD/MM/YYYY (ejemplo: 11/08/2026).",
    "wrong_number": "Número incorrecto, introdúcelo de nuevo.",
    "wrong_time": "Hora incorrecta. Por favor introdúcela en formato HH:MM (ejemplo 11:30) o 0 para omitir.",
    "wrong_choice": "Por favor, responde 'sí' (o 1) o 'no' (o 0).",
    "unauthorized_user": "🔒 Lo siento, este bot es de uso privado.",
    "my_id": "🆔 Tu ID de Telegram es: {}\n\nAñádelo a tu archivo .env como:\nALLOWED_USER_ID={}\npara restringir el bot únicamente a tu usuario.",
    "invalid_filter": "El filtro introducido no es válido o no se encontró ningún tren con estos parámetros, por favor, inténtalo de nuevo con /buscar.",
    "invalid_dwr_token": "Si esto ha ocurrido, Renfe ha actualizado por fin su web. Por favor, abre una issue en github para que pueda revisarlo.",
    "undefined_exception": "Oops, algo se ha roto y no sé el qué. Aquí va toda la traza: {}"
}


def get_tickets_message(trains: List[TrainRideRecord], origin: StationRecord, destination: StationRecord):
    message = (
        f"🎉 *¡Atención! Billete disponible* de {origin.name.title()} a "
        f"{destination.name.title()}:\n\n"
    )
    for train in trains:
        message += str(train)
    return message


def format_initial_train_status(trains: List[TrainRideRecord], origin: StationRecord, destination: StationRecord) -> str:
    msg_str = f"📊 *Estado inicial de trenes ({origin.name.title()} ➔ {destination.name.title()}):*\n\n"
    for train in trains:
        dep_str = train.departure_time.strftime("%H:%M")
        arr_str = train.arrival_time.strftime("%H:%M")
        status_icon = "✅ *Plazas libres*" if train.available else "❌ *Completo (0 plazas libres)*"
        price_str = f" - {train.price:.2f} €" if train.price > 0 else ""
        msg_str += f"• 🚆 *{dep_str} ➔ {arr_str}* ({train.train_type}){price_str}\n  └ {status_icon}\n\n"
    return msg_str
