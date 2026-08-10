"""This module contains the models used in the application"""

from datetime import datetime, time
from typing import List, Optional

from pydantic import BaseModel, Field

from errors import InvalidTrainRideFilter

class StationRecord(BaseModel):
    """Represents a Station, using Renfe's data definition. It can be seen at the file
    assets/station.json"""

    name: str = Field(description="Station name")
    code: str = Field(description="Renfe code for this station")

class TrainRideRecord(BaseModel):
    """Represents a Train ride."""

    origin: str = Field(description="Origin station name")
    destination: str = Field(description="Destination station name")

    departure_time: datetime = Field(description="Departure date and time")
    arrival_time: datetime = Field(description="Estimated arrival date and time")
    duration: int = Field(description="Train ride duration in minutes")

    price: float = Field(description="Train ride price in euros")
    available: bool = Field(description="If the train ride is available for buying a ticket")

    train_type: str = Field(description="Train type")

    def __str__(self):
        date_format = "%H:%M"
        return (
            f"🚆 Tren {self.train_type}: 🕒 {self.departure_time.strftime(date_format)} - "
            f"{self.arrival_time.strftime(date_format)} 🕙 - {self.price:.2f} €\n"
        )

    def  _repr__(self):
        date_format = "%d/%m/%Y %H:%M"
        hours, minutes = divmod(self.duration, 60)
        availability = "Available" if self.available else "Not Available"
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return (f"<TrainRideRecord(train_type={self.train_type}, origin={self.origin}, "
            f"destination={self.destination}, departure_time="
            f"{self.departure_time.strftime(date_format)}, arrival_time="
            f"{self.arrival_time.strftime(date_format)}, duration={duration_str}, "
            f"price={self.price:.2f} €, availability={availability})>")

class TrainRideFilter(BaseModel):
    """Represents filtering criteria for train rides."""
    origin: str
    destination: str

    departure_date: datetime
    max_duration_minutes: Optional[int] = None
    max_price: Optional[float] = None
    max_departure_time: Optional[time] = None

    def get_matching_rides(self, rides: List[TrainRideRecord], include_unavailable: bool = True) -> List[TrainRideRecord]:
        """Filter a list of TrainRideRecord matching parameters, optionally including unavailable ones."""
        filtered_rides = []
        for ride in rides:
            if ride.origin != self.origin or ride.destination != self.destination:
                continue
            if ride.departure_time.date() != self.departure_date.date():
                continue
            if ride.departure_time < self.departure_date:
                continue
            if self.max_departure_time and ride.departure_time.time() > self.max_departure_time:
                continue
            if self.max_duration_minutes and ride.duration > self.max_duration_minutes:
                continue
            if self.max_price and ride.price > self.max_price:
                continue
            if not include_unavailable and not ride.available:
                continue
            filtered_rides.append(ride)
        return filtered_rides

    def filter_rides(self, rides: List[TrainRideRecord]) -> List[TrainRideRecord]:
        """Filter a list of available TrainRideRecord based on user preferences."""
        all_matching = self.get_matching_rides(rides, include_unavailable=True)
        available_matching = [r for r in all_matching if r.available]

        if len(all_matching) == 0:
            raise InvalidTrainRideFilter(
                f"The filter {self} didn't return any result, available or not."
            )
        return available_matching
