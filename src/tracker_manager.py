"""Manages active background tracking tasks for users."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Any

from models import StationRecord


@dataclass
class TrackedSearch:
    id: int
    user_id: int
    origin: StationRecord
    destination: StationRecord
    departure_date: datetime
    max_departure_time: Optional[time] = None
    return_date: Optional[datetime] = None
    max_return_time: Optional[time] = None
    max_price: Optional[float] = None
    max_duration_minutes: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    task: Optional[asyncio.Task] = None

    def get_summary_card(self) -> str:
        summary = (
            f"🔹 *[Rastreo #{self.id}]*\n"
            f"• *Origen:* {self.origin.name.title()}\n"
            f"• *Destino:* {self.destination.name.title()}\n"
            f"• *Salida:* {self.departure_date.strftime('%d/%m/%Y a las %H:%M')}\n"
            f"• *Hora tope salida:* {self.max_departure_time.strftime('%H:%M') if self.max_departure_time else 'Sin límite'}\n"
        )
        if self.return_date:
            summary += f"• *Vuelta:* {self.return_date.strftime('%d/%m/%Y a las %H:%M')}\n"
            summary += f"• *Hora tope vuelta:* {self.max_return_time.strftime('%H:%M') if self.max_return_time else 'Sin límite'}\n"
        if self.max_price:
            summary += f"• *Precio máx:* {self.max_price} €\n"
        if self.max_duration_minutes:
            summary += f"• *Duración máx:* {self.max_duration_minutes} min\n"
        return summary


class TrackerManager:
    """Manages active background tracking tasks for users."""

    def __init__(self):
        self._trackings: Dict[int, TrackedSearch] = {}
        self._counter: int = 0

    def add_tracking(self, search: TrackedSearch) -> int:
        self._counter += 1
        search.id = self._counter
        self._trackings[search.id] = search
        return search.id

    def get_tracking(self, tracking_id: int) -> Optional[TrackedSearch]:
        return self._trackings.get(tracking_id)

    def get_user_trackings(self, user_id: int) -> List[TrackedSearch]:
        return [t for t in self._trackings.values() if t.user_id == user_id]

    def remove_tracking(self, tracking_id: int) -> Optional[TrackedSearch]:
        search = self._trackings.pop(tracking_id, None)
        if search and search.task and not search.task.done():
            search.task.cancel()
        return search

    def cancel_all_user_trackings(self, user_id: int) -> int:
        user_trackings = self.get_user_trackings(user_id)
        count = 0
        for search in user_trackings:
            self.remove_tracking(search.id)
            count += 1
        return count


# Global tracker manager instance
tracker_manager = TrackerManager()
