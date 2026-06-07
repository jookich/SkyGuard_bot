from config import DRONE_LIMITS

def analyze_safety(drone_model: str, wind_speed_ms: float, visibility_km: float):
    """
    Моделирование алгоритма безопасности (блок-схема из п. 1.4)
    Возвращает:
        - status: "safe", "warning", "danger"
        - message: пояснение для пользователя
    """
    limits = DRONE_LIMITS.get(drone_model)
    if not limits:
        return "danger", "❌ Ошибка: модель БПЛА не найдена в базе знаний."
    
    # Первичная проверка: ветер
    if wind_speed_ms > limits["max_wind_ms"]:
        return (
            "danger",
            f"❌ ПОЛЁТ ЗАПРЕЩЁН!\n"
            f"Ветер {wind_speed_ms:.1f} м/с превышает лимит для {drone_model} ({limits['max_wind_ms']} м/с).\n"
            f"Риск потери управления."
        )
    
    # Вторичная проверка: видимость
    if visibility_km < limits["min_visibility_km"]:
        return (
            "danger",
            f"❌ ПОЛЁТ ЗАПРЕЩЁН!\n"
            f"Видимость {visibility_km} км ниже допустимой ({limits['min_visibility_km']} км).\n"
            f"Нарушение визуального контакта с БПЛА."
        )
    
    # Зона внимания (пороги для жёлтого статуса — проектная логика)
    if wind_speed_ms > (limits["max_wind_ms"] * 0.8) or visibility_km < (limits["min_visibility_km"] * 1.2):
        return (
            "warning",
            f"⚠️ ВНИМАНИЕ! Погода на грани допустимого.\n"
            f"Ветер: {wind_speed_ms:.1f} м/с (макс: {limits['max_wind_ms']})\n"
            f"Видимость: {visibility_km} км (мин: {limits['min_visibility_km']})\n"
            f"Рекомендуется перепроверить метеоусловия."
        )
    
    # Полностью безопасно
    return (
        "safe",
        f"✅ ПОЛЁТ РАЗРЕШЁН.\n"
        f"Ветер {wind_speed_ms:.1f} м/с, видимость {visibility_km} км — в пределах нормы для {drone_model}."
    )