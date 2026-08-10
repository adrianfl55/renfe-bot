"""This module contains the validators for the user input"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional
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

            formatted_list = "\n".join(f"{idx+1}. {st.name.title()}" for idx, st in enumerate(suggested_records))
            error_message = (
                f"🔍 No encontré la estación exacta para '{cleaned_name}'. ¿Te refieres a alguna de estas?\n\n"
                f"{formatted_list}\n\n"
                f"💡 Responde con el número (1, 2, 3...) o vuelve a escribir el nombre."
            )
            return StationValidationResult(is_valid=False, error_message=error_message, suggestions=suggested_records)
        else:
            return StationValidationResult(is_valid=False, error_message=msg["station_invalid"])


def validate_date(message: Optional[str]) -> DateValidationResult:
    """Validates the date provided by the user using the dateparser library, that supports
    creating a datetime object from a natural language string in multiple languages"""
    if not message:
        return DateValidationResult(is_valid=False, error_message=msg["wrong_date"])

    parsed_date = dateparser.parse(message,
                                   languages=["es", "en"],
                                   settings={"DATE_ORDER": "DMY"})
    if parsed_date is None:
        return DateValidationResult(is_valid=False, error_message=msg["wrong_date"])
    return DateValidationResult(is_valid=True, date=parsed_date)


def validate_float(message: Optional[str]) -> FloatValidationResult:
    """Validates the float number provided by the user"""
    if not message:
        return FloatValidationResult(is_valid=False, error_message=msg["wrong_number"])
    parsed_number = float(message)
    return FloatValidationResult(is_valid=True, number=parsed_number)


def validate_time(message: Optional[str]) -> TimeValidationResult:
    """Validates the time string provided by the user (e.g. '14:30' or '0' for no limit)"""
    if not message:
        return TimeValidationResult(is_valid=False, error_message=msg["wrong_time"])
    cleaned = message.strip()
    if parse_yes_no(cleaned) is False:
        return TimeValidationResult(is_valid=True, time=None)

    for fmt in ("%H:%M", "%H:%M:%S", "%H.%M"):
        try:
            parsed_time = datetime.strptime(cleaned, fmt).time()
            return TimeValidationResult(is_valid=True, time=parsed_time)
        except ValueError:
            pass

    parsed_dt = dateparser.parse(cleaned, languages=["es", "en"])
    if parsed_dt:
        return TimeValidationResult(is_valid=True, time=parsed_dt.time())

    return TimeValidationResult(is_valid=False, error_message=msg["wrong_time"])
