"""Provider-neutral weather boundary."""

from typing import Protocol

from aideskbuddy.weather.models import WeatherPeriod, WeatherReport


class WeatherProviderError(RuntimeError):
    """Raised when weather data cannot be fetched or validated."""


class WeatherProvider(Protocol):
    async def get_weather(self, period: WeatherPeriod) -> WeatherReport:
        """Return weather for the configured location and period."""
