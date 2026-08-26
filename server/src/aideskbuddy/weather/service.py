"""Cached weather application service."""

import time
from collections.abc import Callable

from aideskbuddy.weather.models import WeatherPeriod, WeatherReport
from aideskbuddy.weather.provider import WeatherProvider


class WeatherService:
    def __init__(
        self,
        provider: WeatherProvider,
        *,
        cache_seconds: float = 600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._cache: dict[WeatherPeriod, tuple[float, WeatherReport]] = {}

    async def get_weather(self, period: WeatherPeriod) -> WeatherReport:
        now = self._clock()
        cached = self._cache.get(period)
        if cached is not None and now - cached[0] < self._cache_seconds:
            return cached[1]
        report = await self._provider.get_weather(period)
        self._cache[period] = (now, report)
        return report
