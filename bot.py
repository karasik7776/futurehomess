import os
import asyncio
import sqlite3
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8693273180:AAHkR8tDpDoP13Cw_FSM-qcoN3Ru1H8gJdE"  # Замени на свой
ADMIN_IDS = [1226310185, 480615667, 1031022066]  # Замени на свой ID

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ========== СПИСКИ ДЛЯ ВОПРОСОВ ==========
ROOMS = ['гостиная', 'спальня', 'кухня', 'детская', 'ванная', 'кабинет', 'прихожая', 'балкон']
SIZES = ['маленькая (до 12 м²)', 'средняя (12–20 м²)', 'большая (20+ м²)', 'не знаю']
WINDOWS = ['нет окон', '1 окно', '2 окна', 'больше 2']
STYLES = ['Современный', 'Минимализм', 'Лофт', 'Скандинавский', 'Прованс', 'Классический', 'Бохо', 'Эко', 'Японский', 'свой вариант']
MOODS = ['уютное', 'строгое', 'романтичное', 'игривое', 'минималистичное', 'яркое', 'спокойное', 'другое']
BUDGETS = ['максимально экономно', 'средний бюджет', 'премиум', 'без разницы']
TONES = ['светлые', 'тёмные', 'смешанные']
ZONES = ['отдых', 'работа', 'приём гостей', 'хранение вещей', 'обеденная зона', 'детский уголок', 'спорт', 'другое']
PEOPLE_COUNTS = ['1', '2-3', '4 и более']
LIGHTINGS = ['естественное + дополнительное', 'только верхний свет', 'много точечных светильников', 'мягкий рассеянный свет', 'яркое белое', 'тёплое жёлтое']
FURNITURE_LIST = ['диван', 'кровать', 'шкаф', 'стол', 'стулья', 'стеллажи', 'пуф', 'телевизор']
TECH_LIST = ['холодильник', 'стиральная машина', 'кондиционер', 'камин', 'проектор', 'нет']
MATERIALS = ['да, предпочту натуральные', 'нет, не принципиально']
PETS = ['кошка', 'собака', 'грызуны', 'нет']

# ========== СОСТОЯНИЯ FSM ==========
class InteriorForm(StatesGroup):
    room = State()
    size = State()
    windows = State()
    style = State()
    custom_style = State()
    mood = State()
    custom_mood = State()
    budget = State()
    colors_want = State()
    colors_not_want = State()
    tones = State()
    zones = State()
    custom_zones = State()
    people_count = State()
    lighting = State()
    furniture = State()
    tech = State()
    materials = State()
    pets = State()
    dislike = State()
    keep = State()
    photos = State()

class AdminState(StatesGroup):
    waiting_for_search_id = State()
    waiting_for_broadcast = State()
    waiting_for_result_text = State()
    waiting_for_chat_reply = State()

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            reg_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            answers TEXT,
            photos TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            from_admin INTEGER,
            message TEXT,
            photo TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, reg_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_request(user_id, answers, photos):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests (user_id, status, created_at, answers, photos)
        VALUES (?, 'pending', ?, ?, ?)
    ''', (user_id, datetime.now().isoformat(), json.dumps(answers, ensure_ascii=False), json.dumps(photos)))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id

def update_request_status(request_id, status):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE requests SET status = ?, completed_at = ? WHERE id = ?
    ''', (status, datetime.now().isoformat(), request_id))
    conn.commit()
    conn.close()

def get_all_requests(status=None):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    if status:
        cursor.execute('SELECT id, user_id, status, created_at FROM requests WHERE status = ? ORDER BY created_at DESC', (status,))
    else:
        cursor.execute('SELECT id, user_id, status, created_at FROM requests ORDER BY created_at DESC')
    requests = cursor.fetchall()
    conn.close()
    return requests

def get_request_by_id(request_id):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, user_id, status, created_at, answers, photos FROM requests WHERE id = ?', (request_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_user_requests(user_id):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, status, created_at FROM requests WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def save_message(request_id, from_admin, message, photo=None):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (request_id, from_admin, message, photo, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (request_id, from_admin, message, photo, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_messages(request_id):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('SELECT from_admin, message, photo, created_at FROM messages WHERE request_id = ? ORDER BY created_at', (request_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(user_id):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🏠 Новый заказ"))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="❓ Помощь"))
    if is_admin(user_id):
        builder.add(KeyboardButton(text="👑 Админ панель"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🆕 Новые заявки"))
    builder.add(KeyboardButton(text="📋 Все заявки"))
    builder.add(KeyboardButton(text="🔍 Поиск заявки"))
    builder.add(KeyboardButton(text="💬 Чат с пользователем"))
    builder.add(KeyboardButton(text="📢 Рассылка"))
    builder.add(KeyboardButton(text="◀️ Выйти из админки"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

def get_room_keyboard():
    builder = ReplyKeyboardBuilder()
    for room in ROOMS:
        builder.add(KeyboardButton(text=room))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_size_keyboard():
    builder = ReplyKeyboardBuilder()
    for size in SIZES:
        builder.add(KeyboardButton(text=size))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_windows_keyboard():
    builder = ReplyKeyboardBuilder()
    for w in WINDOWS:
        builder.add(KeyboardButton(text=w))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_style_keyboard():
    builder = ReplyKeyboardBuilder()
    for style in STYLES:
        builder.add(KeyboardButton(text=style))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_mood_keyboard():
    builder = ReplyKeyboardBuilder()
    for mood in MOODS:
        builder.add(KeyboardButton(text=mood))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_budget_keyboard():
    builder = ReplyKeyboardBuilder()
    for budget in BUDGETS:
        builder.add(KeyboardButton(text=budget))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_tones_keyboard():
    builder = ReplyKeyboardBuilder()
    for tone in TONES:
        builder.add(KeyboardButton(text=tone))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_zones_keyboard():
    builder = ReplyKeyboardBuilder()
    for zone in ZONES:
        builder.add(KeyboardButton(text=zone))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_people_keyboard():
    builder = ReplyKeyboardBuilder()
    for count in PEOPLE_COUNTS:
        builder.add(KeyboardButton(text=count))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_lighting_keyboard():
    builder = ReplyKeyboardBuilder()
    for light in LIGHTINGS:
        builder.add(KeyboardButton(text=light))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_furniture_keyboard():
    builder = ReplyKeyboardBuilder()
    for furniture in FURNITURE_LIST:
        builder.add(KeyboardButton(text=furniture))
    builder.add(KeyboardButton(text="свой вариант"))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_tech_keyboard():
    builder = ReplyKeyboardBuilder()
    for tech in TECH_LIST:
        builder.add(KeyboardButton(text=tech))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_materials_keyboard():
    builder = ReplyKeyboardBuilder()
    for material in MATERIALS:
        builder.add(KeyboardButton(text=material))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_pets_keyboard():
    builder = ReplyKeyboardBuilder()
    for pet in PETS:
        builder.add(KeyboardButton(text=pet))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_photos_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="✅ ГОТОВО"))
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

# ========== ФОРМАТИРОВАНИЕ ==========
def format_answers(answers):
    text = "📋 ВАША АНКЕТА:\n━━━━━━━━━━━━━━━━━━━━\n"
    for key, value in answers.items():
        if value and key != 'photos':
            text += f"▪ {key}: {value}\n"
    return text

def format_request_for_admin(req_id, user_id, status, created_at, answers):
    status_text = "🟡 ОЖИДАЕТ" if status == "pending" else "🟢 ГОТОВ"
    text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ ЗАЯВКА #{req_id}
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃ Статус: {status_text}
┃ Пользователь: {user_id}
┃ Создана: {created_at[:16]}
┣━━━━━━━━━━━━━━━━━━━━━━┫
{format_answers(answers)}
┗━━━━━━━━━━━━━━━━━━━━━━┛
"""
    return text

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username, 
              message.from_user.first_name, message.from_user.last_name)
    
    welcome_text = """
🏠 ДОБРО ПОЖАЛОВАТЬ В "БУДУЩИЙ ДОМ"!

Я помогу создать дизайн-проект вашей комнаты.

КАК РАБОТАТЬ:
1. Нажмите «Новый заказ»
2. Ответьте на вопросы
3. Загрузите 1-3 фото комнаты
4. Получите готовый дизайн от наших специалистов

Удачи! 🎨
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "❓ Помощь")
async def show_help(message: types.Message):
    help_text = """
❓ ПОМОЩЬ

Команды:
/start - Перезапустить бота
/cancel - Отменить заказ

Как создать заказ:
1. Нажмите «Новый заказ»
2. Отвечайте на вопросы
3. В конце загрузите фото

Где посмотреть статус?
Нажмите «Мои заказы»
"""
    await message.answer(help_text)

# ========== ОПРОС ПОЛЬЗОВАТЕЛЯ ==========
@dp.message(F.text == "🏠 Новый заказ")
async def new_order(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(answers={})
    await message.answer("🛋️ СОЗДАДИМ ДИЗАЙН ВАШЕЙ МЕЧТЫ!\n\nВыберите комнату:", reply_markup=get_room_keyboard())
    await state.set_state(InteriorForm.room)

@dp.message(InteriorForm.room)
async def process_room(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in ROOMS:
        await message.answer("Выберите комнату из списка:", reply_markup=get_room_keyboard())
        return
    await state.update_data(answers={"Комната": message.text})
    await message.answer("📏 Какая площадь комнаты?", reply_markup=get_size_keyboard())
    await state.set_state(InteriorForm.size)

@dp.message(InteriorForm.size)
async def process_size(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in SIZES:
        await message.answer("Выберите площадь из списка:", reply_markup=get_size_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Площадь"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🪟 Сколько окон в комнате?", reply_markup=get_windows_keyboard())
    await state.set_state(InteriorForm.windows)

@dp.message(InteriorForm.windows)
async def process_windows(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in WINDOWS:
        await message.answer("Выберите количество окон:", reply_markup=get_windows_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Окна"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🎨 Какой стиль интерьера вам ближе?", reply_markup=get_style_keyboard())
    await state.set_state(InteriorForm.style)

@dp.message(InteriorForm.style)
async def process_style(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text == "свой вариант":
        await message.answer("✏️ Напишите свой вариант стиля:", reply_markup=get_cancel_keyboard())
        await state.set_state(InteriorForm.custom_style)
        return
    if message.text not in STYLES:
        await message.answer("Выберите стиль из списка:", reply_markup=get_style_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Стиль"] = message.text
    await state.update_data(answers=answers)
    await message.answer("😊 Какое настроение хотите создать?", reply_markup=get_mood_keyboard())
    await state.set_state(InteriorForm.mood)

@dp.message(InteriorForm.custom_style)
async def process_custom_style(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Стиль"] = message.text
    await state.update_data(answers=answers)
    await message.answer("😊 Какое настроение хотите создать?", reply_markup=get_mood_keyboard())
    await state.set_state(InteriorForm.mood)

@dp.message(InteriorForm.mood)
async def process_mood(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text == "другое":
        await message.answer("✏️ Напишите своё настроение:", reply_markup=get_cancel_keyboard())
        await state.set_state(InteriorForm.custom_mood)
        return
    if message.text not in MOODS:
        await message.answer("Выберите настроение из списка:", reply_markup=get_mood_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Настроение"] = message.text
    await state.update_data(answers=answers)
    await message.answer("💰 Есть бюджетные ограничения?", reply_markup=get_budget_keyboard())
    await state.set_state(InteriorForm.budget)

@dp.message(InteriorForm.custom_mood)
async def process_custom_mood(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Настроение"] = message.text
    await state.update_data(answers=answers)
    await message.answer("💰 Есть бюджетные ограничения?", reply_markup=get_budget_keyboard())
    await state.set_state(InteriorForm.budget)

@dp.message(InteriorForm.budget)
async def process_budget(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in BUDGETS:
        await message.answer("Выберите бюджет из списка:", reply_markup=get_budget_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Бюджет"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🎨 Какие цвета вы хотите видеть?\n(напишите через запятую)", reply_markup=get_cancel_keyboard())
    await state.set_state(InteriorForm.colors_want)

@dp.message(InteriorForm.colors_want)
async def process_colors_want(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Желаемые цвета"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🚫 Какие цвета НЕ хотите?\n(напишите 'нет' если все ок)", reply_markup=get_cancel_keyboard())
    await state.set_state(InteriorForm.colors_not_want)

@dp.message(InteriorForm.colors_not_want)
async def process_colors_not_want(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Нежелательные цвета"] = message.text if message.text != "нет" else "—"
    await state.update_data(answers=answers)
    await message.answer("🌓 Светлые или тёмные тона?", reply_markup=get_tones_keyboard())
    await state.set_state(InteriorForm.tones)

@dp.message(InteriorForm.tones)
async def process_tones(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in TONES:
        await message.answer("Выберите тона из списка:", reply_markup=get_tones_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Тона"] = message.text
    await state.update_data(answers=answers)
    await message.answer("📍 Какие зоны нужны в комнате?\n(выберите через запятую)", reply_markup=get_zones_keyboard())
    await state.set_state(InteriorForm.zones)

@dp.message(InteriorForm.zones)
async def process_zones(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text == "другое":
        await message.answer("✏️ Напишите какие зоны нужны:", reply_markup=get_cancel_keyboard())
        await state.set_state(InteriorForm.custom_zones)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Зоны"] = message.text
    await state.update_data(answers=answers)
    await message.answer("👥 Сколько человек будут использовать комнату?", reply_markup=get_people_keyboard())
    await state.set_state(InteriorForm.people_count)

@dp.message(InteriorForm.custom_zones)
async def process_custom_zones(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Зоны"] = message.text
    await state.update_data(answers=answers)
    await message.answer("👥 Сколько человек будут использовать комнату?", reply_markup=get_people_keyboard())
    await state.set_state(InteriorForm.people_count)

@dp.message(InteriorForm.people_count)
async def process_people_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in PEOPLE_COUNTS:
        await message.answer("Выберите количество:", reply_markup=get_people_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Количество человек"] = message.text
    await state.update_data(answers=answers)
    await message.answer("💡 Какой тип освещения вам нравится?", reply_markup=get_lighting_keyboard())
    await state.set_state(InteriorForm.lighting)

@dp.message(InteriorForm.lighting)
async def process_lighting(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in LIGHTINGS:
        await message.answer("Выберите освещение:", reply_markup=get_lighting_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Освещение"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🛋️ Какая мебель обязательно должна быть?\n(выберите через запятую)", reply_markup=get_furniture_keyboard())
    await state.set_state(InteriorForm.furniture)

@dp.message(InteriorForm.furniture)
async def process_furniture(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Мебель"] = message.text
    await state.update_data(answers=answers)
    await message.answer("📱 Какая техника есть?\n(выберите через запятую или 'нет')", reply_markup=get_tech_keyboard())
    await state.set_state(InteriorForm.tech)

@dp.message(InteriorForm.tech)
async def process_tech(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Техника"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🌱 Экологические материалы важны?", reply_markup=get_materials_keyboard())
    await state.set_state(InteriorForm.materials)

@dp.message(InteriorForm.materials)
async def process_materials(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in MATERIALS:
        await message.answer("Выберите вариант:", reply_markup=get_materials_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Экоматериалы"] = message.text
    await state.update_data(answers=answers)
    await message.answer("🐕 Есть домашние питомцы?", reply_markup=get_pets_keyboard())
    await state.set_state(InteriorForm.pets)

@dp.message(InteriorForm.pets)
async def process_pets(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    if message.text not in PETS:
        await message.answer("Выберите вариант:", reply_markup=get_pets_keyboard())
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Питомцы"] = message.text
    await state.update_data(answers=answers)
    await message.answer("😞 Что категорически не нравится в текущем интерьере?", reply_markup=get_cancel_keyboard())
    await state.set_state(InteriorForm.dislike)

@dp.message(InteriorForm.dislike)
async def process_dislike(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Что не нравится"] = message.text
    await state.update_data(answers=answers)
    await message.answer("❤️ Что хотите сохранить?\n(напишите 'ничего' если ничего)", reply_markup=get_cancel_keyboard())
    await state.set_state(InteriorForm.keep)

@dp.message(InteriorForm.keep)
async def process_keep(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Сохранить"] = message.text
    await state.update_data(answers=answers)
    
    answers_text = format_answers(answers)
    await message.answer(
        f"{answers_text}\n\n━━━━━━━━━━━━━━━━━━━━\n📸 ТЕПЕРЬ ЗАГРУЗИТЕ ФОТО КОМНАТЫ (1-3 шт)\n\nПросто отправьте фото одно за другим.\nКогда закончите - нажмите «ГОТОВО»",
        reply_markup=get_photos_keyboard()
    )
    await state.set_state(InteriorForm.photos)
    await state.update_data(photos=[])

@dp.message(InteriorForm.photos, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.update_data()
    photos = data.get("photos", [])
    
    if len(photos) >= 3:
        await message.answer("Уже 3 фото. Нажмите «ГОТОВО»")
        return
    
    photo_file_id = message.photo[-1].file_id
    photos.append(photo_file_id)
    await state.update_data(photos=photos)
    
    remaining = 3 - len(photos)
    if remaining > 0:
        await message.answer(f"✅ Фото загружено! Осталось {remaining}. Или нажмите «ГОТОВО»")
    else:
        await message.answer("✅ Загружено 3 фото! Нажмите «ГОТОВО»")

@dp.message(InteriorForm.photos, F.text == "✅ ГОТОВО")
async def finish_photos(message: types.Message, state: FSMContext):
    data = await state.update_data()
    photos = data.get("photos", [])
    answers = data.get("answers", {})
    
    if len(photos) == 0:
        await message.answer("❌ Нужно хотя бы одно фото!")
        return
    
    answers["Количество фото"] = len(photos)
    request_id = save_request(message.from_user.id, answers, photos)
    
    await message.answer(
        f"✅ ЗАЯВКА #{request_id} ПРИНЯТА!\n\nСтатус: Обрабатывается\nСпасибо за доверие! Скоро с вами свяжется дизайнер.",
        reply_markup=get_main_keyboard(message.from_user.id)
    )
    
    # Отправляем уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            await notify_admin(admin_id, request_id, message.from_user.id, answers, photos)
        except Exception as e:
            print(f"Ошибка уведомления админа {admin_id}: {e}")
    
    await state.clear()

@dp.message(InteriorForm.photos)
async def invalid_photos(message: types.Message, state: FSMContext):
    await message.answer("📸 Отправьте фото или нажмите «ГОТОВО»", reply_markup=get_photos_keyboard())

async def notify_admin(admin_id, request_id, user_id, answers, photos):
    text = f"""
🔔 НОВАЯ ЗАЯВКА #{request_id}

👤 Пользователь: {user_id}
🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

{format_answers(answers)}
📸 Фото: {len(photos)} шт.
"""
    await bot.send_message(admin_id, text)
    
    for i, photo_id in enumerate(photos[:3], 1):
        await bot.send_photo(admin_id, photo_id, caption=f"Фото {i}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОТПРАВИТЬ РЕЗУЛЬТАТ", callback_data=f"result_{request_id}")],
        [InlineKeyboardButton(text="💬 НАПИСАТЬ СООБЩЕНИЕ", callback_data=f"chat_{request_id}")]
    ])
    await bot.send_message(admin_id, f"Действия с заявкой #{request_id}:", reply_markup=keyboard)

# ========== МОИ ЗАКАЗЫ ==========
@dp.message(F.text == "📋 Мои заказы")
async def my_orders(message: types.Message):
    orders = get_user_requests(message.from_user.id)
    
    if not orders:
        await message.answer("📭 У вас пока нет заявок. Нажмите «Новый заказ»!")
        return
    
    text = "📋 ВАШИ ЗАЯВКИ:\n━━━━━━━━━━━━━━━━━━━━\n"
    for order in orders:
        status_text = "🟡 В обработке" if order[1] == "pending" else "🟢 Готов"
        text += f"#{order[0]} - {status_text} ({order[2][:10]})\n"
    
    await message.answer(text)

# ========== АДМИНСКИЕ ФУНКЦИИ ==========
@dp.message(F.text == "👑 Админ панель")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа!")
        return
    await message.answer("👑 АДМИН ПАНЕЛЬ\nВыберите действие:", reply_markup=get_admin_keyboard())

@dp.message(F.text == "🆕 Новые заявки")
async def view_new_requests(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    requests = get_all_requests(status='pending')
    
    if not requests:
        await message.answer("📭 Новых заявок нет.")
        return
    
    await message.answer(f"📭 НОВЫЕ ЗАЯВКИ ({len(requests)} шт.)\n━━━━━━━━━━━━━━━━━━━━")
    
    for req in requests:
        req_id, user_id, status, created_at = req
        full_req = get_request_by_id(req_id)
        if not full_req:
            continue
        answers = json.loads(full_req[4])
        photos = json.loads(full_req[5])
        
        text = format_request_for_admin(req_id, user_id, status, created_at, answers)
        await message.answer(text)
        
        if photos:
            for i, photo_id in enumerate(photos[:3], 1):
                await bot.send_photo(message.chat.id, photo_id, caption=f"Фото {i}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ ОТПРАВИТЬ РЕЗУЛЬТАТ", callback_data=f"result_{req_id}")],
            [InlineKeyboardButton(text="💬 НАПИСАТЬ СООБЩЕНИЕ", callback_data=f"chat_{req_id}")]
        ])
        await message.answer(f"Действия с заявкой #{req_id}:", reply_markup=keyboard)

@dp.message(F.text == "📋 Все заявки")
async def view_all_requests_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    requests = get_all_requests()
    
    if not requests:
        await message.answer("📭 Заявок нет.")
        return
    
    text = "📋 ВСЕ ЗАЯВКИ:\n━━━━━━━━━━━━━━━━━━━━\n"
    for req in requests:
        req_id, user_id, status, created_at = req
        status_text = "🟡" if status == "pending" else "🟢"
        text += f"{status_text} #{req_id} | {user_id} | {created_at[:10]}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━\nДля просмотра заявки используйте «Поиск заявки»"
    await message.answer(text)

@dp.message(F.text == "🔍 Поиск заявки")
async def search_request_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите номер заявки для поиска:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminState.waiting_for_search_id)

@dp.message(AdminState.waiting_for_search_id)
async def search_request_by_id(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Поиск отменен.", reply_markup=get_admin_keyboard())
        return
    
    try:
        request_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите ЧИСЛО (номер заявки):")
        return
    
    req = get_request_by_id(request_id)
    if not req:
        await message.answer(f"❌ Заявка #{request_id} не найдена!")
        await state.clear()
        return
    
    req_id, user_id, status, created_at, answers_json, photos_json = req
    answers = json.loads(answers_json)
    photos = json.loads(photos_json)
    
    text = format_request_for_admin(req_id, user_id, status, created_at, answers)
    await message.answer(text)
    
    if photos:
        for i, photo_id in enumerate(photos[:3], 1):
            await bot.send_photo(message.chat.id, photo_id, caption=f"Фото {i}")
    else:
        await message.answer("📸 Фото не загружены")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОТПРАВИТЬ РЕЗУЛЬТАТ", callback_data=f"result_{req_id}")],
        [InlineKeyboardButton(text="💬 НАПИСАТЬ СООБЩЕНИЕ", callback_data=f"chat_{req_id}")]
    ])
    await message.answer(f"Действия с заявкой #{req_id}:", reply_markup=keyboard)
    await state.clear()

@dp.message(F.text == "💬 Чат с пользователем")
async def chat_with_user_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите номер заявки для чата с пользователем:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminState.waiting_for_search_id)

@dp.message(F.text == "📢 Рассылка")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📢 Введите текст для рассылки всем пользователям:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Рассылка отменена.", reply_markup=get_admin_keyboard())
        return
    
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    await message.answer(f"🚀 Начинаю рассылку {len(users)} пользователям...")
    
    success = 0
    fail = 0
    
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 ОБЪЯВЛЕНИЕ\n\n{message.text}")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await message.answer(f"✅ РАССЫЛКА ЗАВЕРШЕНА!\nУспешно: {success}\nОшибок: {fail}", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "◀️ Выйти из админки")
async def exit_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Выход из админ-панели.", reply_markup=get_main_keyboard(message.from_user.id))

# ========== ОТПРАВКА РЕЗУЛЬТАТА ==========
@dp.callback_query(lambda c: c.data and c.data.startswith('result_'))
async def send_result_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split('_')[1])
    await state.update_data(result_request_id=request_id)
    
    await callback.message.answer(f"✍️ ОТПРАВКА РЕЗУЛЬТАТА ДЛЯ ЗАЯВКИ #{request_id}\n\nВведите текст и отправьте. Можете приложить фото.\nПосле отправки заявка автоматически станет ВЫПОЛНЕННОЙ.", reply_markup=get_cancel_keyboard())
    await callback.answer()
    await state.set_state(AdminState.waiting_for_result_text)

@dp.message(AdminState.waiting_for_result_text)
async def process_result(message: types.Message, state: FSMContext):
    if message.text and message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Отмена.", reply_markup=get_admin_keyboard())
        return
    
    data = await state.update_data()
    request_id = data.get('result_request_id')
    
    if not request_id:
        await message.answer("Ошибка: не найден ID заявки")
        await state.clear()
        return
    
    req = get_request_by_id(request_id)
    if not req:
        await message.answer("Заявка не найдена!")
        await state.clear()
        return
    
    user_id = req[1]
    reply_text = message.text if message.text else "Ваш дизайн-проект готов!"
    
    # Отправляем результат пользователю
    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = f"🏠 ВАШ ДИЗАЙН-ПРОЕКТ ГОТОВ!\n\nЗаявка #{request_id}\n\n{reply_text}"
        await bot.send_photo(user_id, photo_id, caption=caption)
    elif message.document:
        await bot.send_document(user_id, message.document.file_id, caption=reply_text)
    else:
        await bot.send_message(user_id, f"🏠 ВАШ ДИЗАЙН-ПРОЕКТ ГОТОВ!\n\nЗаявка #{request_id}\n\n{reply_text}")
    
    # Обновляем статус
    update_request_status(request_id, 'completed')
    
    await message.answer(f"✅ РЕЗУЛЬТАТ ОТПРАВЛЕН!\nЗаявка #{request_id} закрыта.", reply_markup=get_admin_keyboard())
    await state.clear()

# ========== ЧАТ С ПОЛЬЗОВАТЕЛЕМ ==========
@dp.callback_query(lambda c: c.data and c.data.startswith('chat_'))
async def chat_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split('_')[1])
    req = get_request_by_id(request_id)
    
    if not req:
        await callback.message.answer("Заявка не найдена!")
        await callback.answer()
        return
    
    user_id = req[1]
    
    await state.update_data(chat_request_id=request_id, chat_user_id=user_id)
    
    # Показываем историю
    messages = get_messages(request_id)
    if messages:
        history = "📜 ИСТОРИЯ ПЕРЕПИСКИ:\n━━━━━━━━━━━━━━━━━━━━\n"
        for msg in messages:
            from_admin, text, photo, created_at = msg
            sender = "Админ" if from_admin else "Клиент"
            history += f"[{created_at[11:16]}] {sender}: {text if text else '[Фото]'}\n"
        await callback.message.answer(history)
    
    await callback.message.answer(f"💬 ЧАТ С ПОЛЬЗОВАТЕЛЕМ (заявка #{request_id})\n\nПросто отправьте сообщение, оно будет доставлено пользователю.\n\nЧтобы выйти, нажмите «❌ Отменить»", reply_markup=get_cancel_keyboard())
    await callback.answer()
    await state.set_state(AdminState.waiting_for_chat_reply)

@dp.message(AdminState.waiting_for_chat_reply)
async def chat_send_to_user(message: types.Message, state: FSMContext):
    if message.text and message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Чат закрыт.", reply_markup=get_admin_keyboard())
        return
    
    data = await state.update_data()
    request_id = data.get('chat_request_id')
    user_id = data.get('chat_user_id')
    
    if not request_id or not user_id:
        await message.answer("Ошибка: чат не инициализирован")
        await state.clear()
        return
    
    try:
        if message.photo:
            photo_id = message.photo[-1].file_id
            caption = message.caption if message.caption else ""
            await bot.send_photo(user_id, photo_id, caption=f"💬 Сообщение от дизайнера:\n\n{caption}")
            save_message(request_id, 1, caption or "Фото", photo_id)
        elif message.text:
            await bot.send_message(user_id, f"💬 Сообщение от дизайнера:\n\n{message.text}")
            save_message(request_id, 1, message.text, None)
        else:
            await message.answer("Поддерживаются только текст и фото")
            return
        
        await message.answer("✅ Сообщение отправлено пользователю!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

# ========== ПРИЕМ СООБЩЕНИЙ ОТ ПОЛЬЗОВАТЕЛЕЙ ==========
@dp.message(F.text)
async def handle_user_message(message: types.Message, state: FSMContext):
    # Проверяем, что это не команда и не кнопка
    if message.text.startswith('/'):
        return
    
    # Проверяем, находится ли пользователь в процессе опроса
    current_state = await state.get_state()
    if current_state and current_state.startswith('InteriorForm'):
        return
    
    # Игнорируем системные кнопки
    system_buttons = ['🏠 Новый заказ', '📋 Мои заказы', '❓ Помощь', '👑 Админ панель', 
                      '🆕 Новые заявки', '📋 Все заявки', '🔍 Поиск заявки', '💬 Чат с пользователем', 
                      '📢 Рассылка', '◀️ Выйти из админки', '❌ Отменить', '✅ ГОТОВО']
    if message.text in system_buttons:
        return
    
    # Находим последнюю заявку пользователя
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (message.from_user.id,))
    last_request = cursor.fetchone()
    conn.close()
    
    if last_request:
        request_id = last_request[0]
        save_message(request_id, 0, message.text, None)
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"💬 НОВОЕ СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ\n\nЗаявка #{request_id}\n\n{message.text}\n\nЧтобы ответить, используйте «💬 Чат с пользователем» и введите {request_id}")

# ========== ОТМЕНА ==========
@dp.message(F.text == "❌ Отменить")
async def cancel_order(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and 'AdminState' in current_state:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_admin_keyboard())
    else:
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await cancel_order(message, state)

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
