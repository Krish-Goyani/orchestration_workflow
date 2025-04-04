from typing import Any

import httpx

from src.config.settings import settings
from src.tools.tool_decorator import tool

API_ENDPOINT = f"https://api.openweathermap.org/data/2.5/weather?q={{location}}&APPID={settings.WEATHER_API_KEY}"


async def make_weather_request(url: str) -> dict[str, Any] | None:
    "make a weather request to the given url"
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url=url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(e)
            return None


@tool()
async def get_forecast(city: str) -> str:
    """Get weather forecast for a location.

    Args:
        city: name of the city whose temperature is to be fetched
    Returns:
        str: temperature for the given location
    """
    data = await make_weather_request(API_ENDPOINT.format(location=city))
    if not data:
        return "Failed to fetch weather data"

    # Convert Kelvin to Celsius
    temp_celsius = round(data['main']['temp'] - 273.15, 1)
    return f"The weather in {city} is {data['weather'][0]['description']} with a temperature of {temp_celsius}°C."
