"""Open-Meteo weather provider adapter."""

from datetime import date
from typing import Any

import httpx

from aideskbuddy.weather.models import WeatherPeriod, WeatherReport
from aideskbuddy.weather.provider import WeatherProviderError

_WEATHER_CONDITIONS = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy with frost",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "light snow showers",
    86: "heavy snow showers",
    95: "thunderstorms",
    96: "thunderstorms with light hail",
    99: "thunderstorms with heavy hail",
}


class OpenMeteoWeatherProvider:
    """Fetch current conditions and a two-day forecast from Open-Meteo."""

    def __init__(
        self,
        *,
        latitude: float,
        longitude: float,
        location_name: str,
        timezone: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._location_name = location_name
        self._timezone = timezone
        self._client = client

    async def get_weather(self, period: WeatherPeriod) -> WeatherReport:
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "timezone": self._timezone,
            "forecast_days": 2,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum,wind_speed_10m_max"
            ),
        }
        try:
            if self._client is not None:
                response = await self._client.get("/v1/forecast", params=params)
            else:
                async with httpx.AsyncClient(
                    base_url="https://api.open-meteo.com", timeout=5.0
                ) as client:
                    response = await client.get("/v1/forecast", params=params)
            response.raise_for_status()
            payload = response.json()
            return self._parse(payload, period)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError) as exc:
            raise WeatherProviderError("weather service unavailable") from exc

    def _parse(self, payload: dict[str, Any], period: WeatherPeriod) -> WeatherReport:
        daily = payload["daily"]
        day_index = 1 if period == "tomorrow" else 0
        current = payload["current"]
        code = int(
            current["weather_code"]
            if period == "now"
            else daily["weather_code"][day_index]
        )
        return WeatherReport(
            location=self._location_name,
            period=period,
            date=date.fromisoformat(daily["time"][day_index]),
            condition=_WEATHER_CONDITIONS.get(code, "unknown conditions"),
            current_temperature_c=(
                float(current["temperature_2m"]) if period != "tomorrow" else None
            ),
            apparent_temperature_c=(
                float(current["apparent_temperature"]) if period != "tomorrow" else None
            ),
            minimum_temperature_c=float(daily["temperature_2m_min"][day_index]),
            maximum_temperature_c=float(daily["temperature_2m_max"][day_index]),
            precipitation_probability_percent=int(
                daily["precipitation_probability_max"][day_index]
            ),
            precipitation_sum_mm=float(daily["precipitation_sum"][day_index]),
            maximum_wind_speed_kmh=float(daily["wind_speed_10m_max"][day_index]),
        )
