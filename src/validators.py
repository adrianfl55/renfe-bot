"""This module contains the validators for the user input"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional
import re
import unicodedata

import dateparser

from errors import StationNotFound
from messages import user_messages as msg
from models import StationRecord
from storage import StationsStorage


def normalize_text(text: Optional[str]) -> str:
    """Strips whitespace, converts to lowercase, and removes accents/diacritics."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def parse_yes_no(text: Optional[str]) -> Optional[bool]:
    """Parses yes/no answers accepting variants like 'sí', 'si', 'SÍ', '1', 'no', '0', etc."""
    normalized = normalize_text(text)
    if normalized in ["si", "s", "1", "y", "yes", "true"]:
        return True
    if normalized in ["no", "n", "0", "false"]:
        return False
    return None


@dataclass
class StationValidationResult:
    """Holds the result of station validation"""

    is_valid: bool
    station: StationRecord | None = None
    error_message: str = ""
    suggestions: list[StationRecord] = field(default_factory=list)

    def __bool__(self):
        return self.is_valid


@dataclass
class DateValidationResult:
    """Holds the result of date validation"""

    is_valid: bool
    date: datetime | None = None
    error_message: str = ""

    def __bool__(self):
        return self.is_valid

@dataclass
class FloatValidationResult:
    """Holds the result of a float number validation"""

    is_valid: bool
    number: float | None = None
    error_message: str = ""

    def __bool__(self):
        return self.is_valid


@dataclass
class TimeValidationResult:
    """Holds the result of a time validation"""

    is_valid: bool
    time: Optional[time] = None
    error_message: str = ""

    def __bool__(self):
        return self.is_valid


def validate_station(station_name: Optional[str]) -> StationValidationResult:
    """Validates the station provided by the user, returning partial matches if the station is
    not found"""
    if not station_name or not station_name.strip():
        return StationValidationResult(is_valid=False, error_message=msg["station_invalid"])

    cleaned_name = station_name.strip()

    try:
        station = StationsStorage.get_station(cleaned_name.upper())
        return StationValidationResult(is_valid=True, station=station)
    except StationNotFound:
        possible_stations = StationsStorage.find_station(cleaned_name)
        if len(possible_stations) == 1:
            station = StationsStorage.get_station(possible_stations[0])
            return StationValidationResult(is_valid=True, station=station)
        elif len(possible_stations) > 1:
            suggested_records: list[StationRecord] = []
            for st_name in possible_stations[:6]:
                try:
                    st_rec = StationsStorage.get_station(st_name)
                    suggested_records.append(st_rec)
                except StationNotFound:
                    pass

            error_message = msg["station_not_found"].format(cleaned_name)
            return StationValidationResult(is_valid=False, error_message=error_message, suggestions=suggested_records)
        else:
            return StationValidationResult(is_valid=False, error_message=msg["station_invalid"])


def validate_date(message: Optional[str]) -> DateValidationResult:
    """Validates the date provided by the user strictly (DD/MM/YYYY) and ensures it is not in the past."""
    if not message:
        return DateValidationResult(is_valid=False, error_message=msg["wrong_date"])

    cleaned = message.strip()
    parsed_date = None

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            parsed_dt = datetime.strptime(cleaned, fmt)
            parsed_date = parsed_dt
            break
        except ValueError:
            pass

    if parsed_date is None:
        return DateValidationResult(
            is_valid=False,
            error_message="⚠️ Formato de fecha incorrecto. Por favor, introdúcela en formato *DD/MM/YYYY* (ejemplo: 11/08/2026)."
        )

    today_start = datetime.combine(datetime.now().date(), time.min)
    if parsed_date < today_start:
        return DateValidationResult(
            is_valid=False,
            error_message="⚠️ La fecha no puede ser anterior al día de hoy. Por favor, introduce una fecha futura (ejemplo: 11/08/2026)."
        )

    return DateValidationResult(is_valid=True, date=parsed_date)


def validate_float(message: Optional[str]) -> FloatValidationResult:
    """Validates the float number provided by the user"""
    if not message:
        return FloatValidationResult(is_valid=False, error_message=msg["wrong_number"])
    try:
        parsed_number = float(message.replace(",", ".").strip())
        return FloatValidationResult(is_valid=True, number=parsed_number)
    except ValueError:
        return FloatValidationResult(is_valid=False, error_message=msg["wrong_number"])


def validate_time(message: Optional[str]) -> TimeValidationResult:
    """Validates strict time format HH:MM (00:00 to 23:59) or '0'/'no' for no limit."""
    if not message:
        return TimeValidationResult(is_valid=False, error_message=msg["wrong_time"])

    cleaned = message.strip().lower()

    if cleaned in ("0", "00", "00:00", "no", "n", "cero", "ninguno", "ninguna", "false"):
        return TimeValidationResult(is_valid=True, time=None)

    match = re.match(r"^([0-1]?[0-9]|2[0-3])[:.]([0-5][0-9])$", cleaned)
    if not match:
        return TimeValidationResult(
            is_valid=False,
            error_message="⚠️ Formato de hora incorrecto. Introduce la hora en formato *HH:MM* (ejemplo: 11:30) o responde *0* para sin límite de hora."
        )

    hours, minutes = int(match.group(1)), int(match.group(2))
    parsed_time = time(hour=hours, minute=minutes)
    return TimeValidationResult(is_valid=True, time=parsed_time)
