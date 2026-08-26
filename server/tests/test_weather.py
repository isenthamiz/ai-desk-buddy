"""Tests for weather fetching, parsing, and caching."""

import httpx
import pytest

from aideskbuddy.weather import OpenMeteoWeatherProvider, WeatherService


def _payload() -> dict[str, object]:
    return {
        "current": {
            "temperature_2m": 15.2,
            "apparent_temperature": 14.1,
            "weather_code": 2,
        },
        "daily": {
            "time": ["2026-08-26", "2026-08-27"],
            "weather_code": [61, 3],
            "temperature_2m_max": [18.4, 17.0],
            "temperature_2m_min": [10.2, 9.5],
            "precipitation_probability_max": [70, 20],
            "precipitation_sum": [2.8, 0.1],
            "wind_speed_10m_max": [25.0, 18.0],
        },
    }


@pytest.mark.asyncio
async def test_open_meteo_parses_current_and_tomorrow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timezone"] == "Europe/Dublin"
        assert request.url.params["forecast_days"] == "2"
        return httpx.Response(200, json=_payload())

    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = OpenMeteoWeatherProvider(
            latitude=53.3498,
            longitude=-6.2603,
            location_name="Dublin",
            timezone="Europe/Dublin",
            client=client,
        )
        current = await provider.get_weather("now")
        tomorrow = await provider.get_weather("tomorrow")

    assert current.condition == "partly cloudy"
    assert current.current_temperature_c == 15.2
    assert current.precipitation_probability_percent == 70
    assert tomorrow.condition == "overcast"
    assert tomorrow.current_temperature_c is None
    assert tomorrow.maximum_temperature_c == 17.0


@pytest.mark.asyncio
async def test_weather_service_caches_each_period() -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def get_weather(self, period):
            self.calls += 1
            async with httpx.AsyncClient(
                base_url="https://api.open-meteo.com",
                transport=httpx.MockTransport(
                    lambda _request: httpx.Response(200, json=_payload())
                ),
            ) as client:
                return await OpenMeteoWeatherProvider(
                    latitude=53.3498,
                    longitude=-6.2603,
                    location_name="Dublin",
                    timezone="Europe/Dublin",
                    client=client,
                ).get_weather(period)

    provider = FakeProvider()
    service = WeatherService(provider, cache_seconds=600, clock=lambda: 10.0)

    first = await service.get_weather("today")
    second = await service.get_weather("today")

    assert first is second
    assert provider.calls == 1
