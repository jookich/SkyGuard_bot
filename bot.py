import asyncio
import logging
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, AVAILABLE_DRONES
from weather_api import get_weather_by_coords
from safety_logic import analyze_safety

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session = AiohttpSession(api=TelegramAPIServer.from_base('http://185.162.228.151:80'))
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM для диалога
class DroneDialog(StatesGroup):
    waiting_for_drone_model = State()    # выбор модели
    waiting_for_coords = State()         # ожидание геопозиции

# Главная клавиатура с кнопками-командами
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛸 Проверить погоду")],
        [KeyboardButton(text="⚙️ Настройки лимитов")]
    ],
    resize_keyboard=True
)

# Inline-клавиатура для выбора модели дрона
def get_drone_keyboard():
    buttons = []
    for model in AVAILABLE_DRONES:
        buttons.append([InlineKeyboardButton(text=model, callback_data=f"drone_{model}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команда /start — начало работы
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "✈️ *Добро пожаловать в систему метеомониторинга БПЛА!*\n\n"
        "Я — ваш советник по безопасности полётов.\n"
        "Сначала выберите модель вашего беспилотника из базы знаний:",
        reply_markup=get_drone_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(DroneDialog.waiting_for_drone_model)

# Обработка выбора модели
@dp.callback_query(StateFilter(DroneDialog.waiting_for_drone_model), F.data.startswith("drone_"))
async def process_drone_selection(callback: CallbackQuery, state: FSMContext):
    drone_model = callback.data.replace("drone_", "")
    await state.update_data(drone_model=drone_model)
    
    await callback.message.edit_text(
        f"✅ Модель выбрана: *{drone_model}*\n\n"
        f"Теперь нажмите кнопку *«Проверить погоду»* и поделитесь геолокацией, "
        f"либо отправьте координаты вручную (широта,долгота):\n"
        f"Пример: `55.751244,37.618423`",
        parse_mode="Markdown"
    )
    await callback.answer()
    await state.set_state(DroneDialog.waiting_for_coords)
    await callback.message.answer("Выберите действие:", reply_markup=main_keyboard)

# Кнопка "Проверить погоду" — ИСПРАВЛЕНО: убрано ограничение по состоянию
@dp.message(F.text == "🛸 Проверить погоду")
async def ask_location(message: Message, state: FSMContext):
    # Проверяем, выбрана ли модель
    user_data = await state.get_data()
    drone_model = user_data.get("drone_model")
    
    if not drone_model:
        await message.answer(
            "❌ Сначала выберите модель беспилотника.\n"
            "Введите команду /start"
        )
        return
    
    await state.set_state(DroneDialog.waiting_for_coords)
    await message.answer(
        "📍 Отправьте геолокацию (нажмите скрепку → 📍 Location) "
        "или введите координаты в формате: широта,долгота\n"
        "Пример: 55.751244,37.618423"
    )

# Кнопка "Настройки лимитов" — ИСПРАВЛЕНО: добавлен полноценный функционал
@dp.message(F.text == "⚙️ Настройки лимитов")
async def settings_command(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_drone = user_data.get("drone_model")
    
    from config import DRONE_LIMITS
    
    if current_drone and current_drone in DRONE_LIMITS:
        limits = DRONE_LIMITS[current_drone]
        settings_text = (
            f"⚙️ *Текущие лимиты безопасности*\n\n"
            f"📱 Модель: *{current_drone}*\n"
            f"💨 Макс. скорость ветра: *{limits['max_wind_ms']} м/с*\n"
            f"👁 Мин. видимость: *{limits['min_visibility_km']} км*\n\n"
            f"ℹ️ В текущей версии изменить лимиты можно только через выбор другой модели.\n"
            f"Для смены модели введите /start"
        )
    else:
        settings_text = (
            f"⚙️ *Настройки системы*\n\n"
            f"Модель БПЛА не выбрана.\n"
            f"Для начала работы введите /start и выберите модель дрона.\n\n"
            f"*Доступные модели:*\n"
        )
        for model, limits in DRONE_LIMITS.items():
            settings_text += f"• {model}: ветер ≤{limits['max_wind_ms']} м/с, видимость ≥{limits['min_visibility_km']} км\n"
    
    await message.answer(settings_text, parse_mode="Markdown")

# Обработка геолокации
@dp.message(F.location)
async def handle_geo(message: Message, state: FSMContext):
    # Проверяем состояние (если не в режиме ожидания координат — не обрабатываем)
    current_state = await state.get_state()
    if current_state != DroneDialog.waiting_for_coords:
        await message.answer(
            "🔔 Сначала выберите действие.\n"
            "Нажмите '🛸 Проверить погоду' или введите /start"
        )
        return
    
    lat = message.location.latitude
    lon = message.location.longitude
    await process_weather_check(message, state, lat, lon)

# Обработка ручного ввода координат
@dp.message(F.text)
async def handle_text_coords(message: Message, state: FSMContext):
    # Пропускаем команды и кнопки
    if message.text.startswith("/") or message.text in ["🛸 Проверить погоду", "⚙️ Настройки лимитов"]:
        return
    
    # Проверяем состояние
    current_state = await state.get_state()
    if current_state != DroneDialog.waiting_for_coords:
        # Если не ждём координаты — показываем меню
        await message.answer(
            "Используйте кнопки меню для работы с ботом.\n"
            "Если вы не выбрали модель, введите /start",
            reply_markup=main_keyboard
        )
        return
    
    text = message.text.strip()
    # Валидация координат
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        await message.answer("❌ Ошибка: введите координаты через пробел или запятую.\nПример: 55.7512 37.6184")
        return
    
    try:
        lat = float(parts[0])
        lon = float(parts[1])
        # Проверка диапазонов
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            await message.answer("❌ Ошибка: широта должна быть от -90 до 90, долгота от -180 до 180.")
            return
        await process_weather_check(message, state, lat, lon)
    except ValueError:
        await message.answer("❌ Неверный формат чисел. Используйте точки, например: 55.7512 37.6184")

async def process_weather_check(message: Message, state: FSMContext, lat: float, lon: float):
    """Основной алгоритм: запрос погоды -> анализ -> вывод с цветовой индикацией"""
    user_data = await state.get_data()
    drone_model = user_data.get("drone_model")
    
    if not drone_model:
        await message.answer("❌ Модель не найдена. Введите /start для выбора модели.")
        await state.clear()
        return
    
    # Отправляем статус "печатает"
    await bot.send_chat_action(message.chat.id, action="typing")
    
    # Получаем данные от API
    weather = await get_weather_by_coords(lat, lon)
    if not weather:
        await message.answer(
            "🌐 Ошибка подключения к метеосерверу.\n"
            "Проверьте интернет-соединение или попробуйте позже."
        )
        return
    
    # Логический анализ
    status, safety_msg = analyze_safety(
        drone_model,
        weather["wind_speed_ms"],
        weather["visibility_km"]
    )
    
    # Выбор эмодзи статуса
    status_emoji = {
        "safe": "🟢",
        "warning": "🟠",
        "danger": "🔴"
    }.get(status, "⚪")
    
    # Формируем подробный отчёт
    report = (
        f"{status_emoji} *Метеосводка для {drone_model}*\n"
        f"📍 *Координаты:* {lat:.4f}, {lon:.4f}\n"
        f"🌡 *Температура:* {weather['temperature']:.1f}°C\n"
        f"💨 *Ветер:* {weather['wind_speed_ms']:.1f} м/с\n"
        f"👁 *Видимость:* {weather['visibility_km']} км\n"
        f"💧 *Влажность:* {weather['humidity']}%\n"
        f"📋 *Условия:* {weather['description']}\n\n"
        f"{safety_msg}"
    )
    
    # Экстренные рекомендации согласно дизайну (п. 2.5)
    if status == "danger":
        report += "\n\n🚨 *ЭКСТРЕННАЯ РЕКОМЕНДАЦИЯ:* Выполните экстренную посадку! Полёт запрещён."
    elif status == "warning":
        report += "\n\n⚠️ *Рекомендация:* Будьте внимательны при планировании маршрута. Рекомендуется перепроверить условия."
    else:
        report += "\n\n✅ *Рекомендация:* Можно выполнять полёт в соответствии с заданием."
    
    await message.answer(report, parse_mode="Markdown")
    
    # После успешной проверки возвращаемся в состояние ожидания новых запросов
    await state.set_state(DroneDialog.waiting_for_coords)

# Обработка callback-запросов от inline-клавиатур (на случай, если пользователь нажал на модель после старта)
@dp.callback_query(F.data.startswith("drone_"))
async def callback_drone_selection(callback: CallbackQuery, state: FSMContext):
    drone_model = callback.data.replace("drone_", "")
    await state.update_data(drone_model=drone_model)
    await state.set_state(DroneDialog.waiting_for_coords)
    
    await callback.message.answer(
        f"✅ Модель изменена на: *{drone_model}*\n\n"
        f"Теперь нажмите кнопку *«Проверить погоду»*",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

async def main():
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())