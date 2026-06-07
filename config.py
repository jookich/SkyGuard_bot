
BOT_TOKEN = "8654342844:AAGdHy9WzMXGh1eLL3W8vC_yhHU1lZYAEs0"
OPENWEATHER_API_KEY = "a77ce629a39f14abe9bff5502ebc0b55"

# База знаний: лимиты безопасности для популярных моделей БПЛА
# (как описано в п. 2.1 проектной документации)
DRONE_LIMITS = {
    "DJI Mavic 3": {
        "max_wind_ms": 10.0,      # максимальный ветер м/с
        "min_visibility_km": 1.0, # минимальная видимость км
        "name": "DJI Mavic 3"
    },
    "DJI Mini 4 Pro": {
        "max_wind_ms": 8.0,
        "min_visibility_km": 1.0,
        "name": "DJI Mini 4 Pro"
    },
    "Autel Evo Lite+": {
        "max_wind_ms": 9.0,
        "min_visibility_km": 1.0,
        "name": "Autel Evo Lite+"
    },
    "Matrice 350 RTK": {
        "max_wind_ms": 12.0,
        "min_visibility_km": 0.5,
        "name": "Matrice 350 RTK"
    }
}

# Доступные модели для выбора (UI)
AVAILABLE_DRONES = list(DRONE_LIMITS.keys())

# Цветовые статусы (п. 2.5 дизайн)
STATUS_COLORS = {
    "safe": "🟢",      # зелёный — полёт разрешён
    "warning": "🟠",   # оранжевый — внимание
    "danger": "🔴"     # красный — запрет
}