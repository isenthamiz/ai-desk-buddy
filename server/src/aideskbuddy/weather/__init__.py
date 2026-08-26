"""Weather reporting services and provider adapters."""

from aideskbuddy.weather.models import WeatherPeriod, WeatherReport
from aideskbuddy.weather.open_meteo import OpenMeteoWeatherProvider
from aideskbuddy.weather.provider import WeatherProvider, WeatherProviderError
from aideskbuddy.weather.service import WeatherService

__all__ = [
    "OpenMeteoWeatherProvider",
    "WeatherPeriod",
    "WeatherProvider",
    "WeatherProviderError",
    "WeatherReport",
    "WeatherService",
]
