import aiohttp
from config import OPENWEATHER_API_KEY  # больше не нужен, но оставим для совместимости

async def get_weather_by_coords(lat: float, lon: float):
    """
    Асинхронный запрос к Open-Meteo API (бесплатно, без ключа, работает из России)
    Документация: https://open-meteo.com/en/docs
    """
    # Open-Meteo позволяет получить все нужные параметры в одном запросе
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,pressure_msl,visibility,weather_code",
        "wind_speed_unit": "ms",  # ветер в м/с
        "timezone": "auto"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return None
            
            data = await resp.json()
            current = data.get("current", {})
            
            # Преобразуем weather_code в понятное описание
            weather_code = current.get("weather_code", 0)
            weather_desc = translate_weather_code(weather_code)
            
            # В Open-Meteo visibility возвращается в метрах
            visibility_m = current.get("visibility", 10000)
            
            return {
                "wind_speed_ms": current.get("wind_speed_10m", 0),
                "visibility_km": round(visibility_m / 1000, 1),
                "temperature": current.get("temperature_2m", 0),
                "pressure": current.get("pressure_msl", 0),
                "humidity": current.get("relative_humidity_2m", 0),
                "description": weather_desc,
                "city": f"{lat:.2f}, {lon:.2f}"  # Open-Meteo не возвращает название города
            }

def translate_weather_code(code: int) -> str:
    """Перевод кодов погоды Open-Meteo в человекочитаемый формат"""
    weather_codes = {
        0: "Ясно",
        1: "В основном ясно",
        2: "Переменная облачность",
        3: "Пасмурно",
        45: "Туман",
        48: "Туман с изморозью",
        51: "Морось (слабая)",
        53: "Морось (умеренная)",
        55: "Морось (сильная)",
        61: "Дождь (слабый)",
        63: "Дождь (умеренный)",
        65: "Дождь (сильный)",
        71: "Снег (слабый)",
        73: "Снег (умеренный)",
        75: "Снег (сильный)",
        77: "Снежная крупа",
        80: "Ливень (слабый)",
        81: "Ливень (умеренный)",
        82: "Ливень (сильный)",
        95: "Гроза",
        96: "Гроза с градом",
        99: "Гроза с сильным градом"
    }
    return weather_codes.get(code, "Неизвестно")