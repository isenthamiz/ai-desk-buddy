"""Provider-neutral weather models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

WeatherPeriod = Literal["now", "today", "tomorrow"]


class WeatherReport(BaseModel):
    """Small set of conditions useful for a concise spoken report."""

    model_config = ConfigDict(frozen=True)

    location: str
    period: WeatherPeriod
    date: date
    condition: str
    current_temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    minimum_temperature_c: float
    maximum_temperature_c: float
    precipitation_probability_percent: int
    precipitation_sum_mm: float
    maximum_wind_speed_kmh: float
