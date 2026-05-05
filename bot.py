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
    waiting_for_reply_text = State()
    waiting_for_broadcast = State()
    waiting_for_photo_for_reply = State()

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

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(is_admin=False):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🏠 Новый заказ"))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="❓ Помощь"))
    if is_admin:
        builder.add(KeyboardButton(text="👑 Админ панель"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🆕 Новые заявки"))
    builder.add(KeyboardButton(text="📋 Все заявки"))
    builder.add(KeyboardButton(text="📢 Рассылка"))
    builder.add(KeyboardButton(text="◀️ Выйти из админки"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

# ========== ФОРМАТИРОВАНИЕ (без HTML) ==========
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

СОВЕТЫ:
• Отвечайте подробно
• Фото делайте при хорошем освещении
• Можно отменить заказ в любой момент

Удачи! 🎨
"""
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_admin))

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

По всем вопросам пишите админу.
"""
    await message.answer(help_text)

@dp.message(F.text == "🏠 Новый заказ")
async def new_order(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(answers={})
    await message.answer(
        "🛋️ СОЗДАДИМ ДИЗАЙН ВАШЕЙ МЕЧТЫ!\n\nВыберите комнату:",
        reply_markup=get_room_keyboard()
    )
    await state.set_state(InteriorForm.room)

def get_room_keyboard():
    builder = ReplyKeyboardBuilder()
    for room in ROOMS:
        builder.add(KeyboardButton(text=room))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_size_keyboard():
    builder = ReplyKeyboardBuilder()
    for size in SIZES:
        builder.add(KeyboardButton(text=size))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_windows_keyboard():
    builder = ReplyKeyboardBuilder()
    for w in WINDOWS:
        builder.add(KeyboardButton(text=w))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_style_keyboard():
    builder = ReplyKeyboardBuilder()
    for style in STYLES:
        builder.add(KeyboardButton(text=style))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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
    await ask_mood(message, state)

async def ask_mood(message: types.Message, state: FSMContext):
    await message.answer("😊 Какое настроение хотите создать?", reply_markup=get_mood_keyboard())
    await state.set_state(InteriorForm.mood)

def get_mood_keyboard():
    builder = ReplyKeyboardBuilder()
    for mood in MOODS:
        builder.add(KeyboardButton(text=mood))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(InteriorForm.custom_style)
async def process_custom_style(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Стиль"] = message.text
    await state.update_data(answers=answers)
    await ask_mood(message, state)

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

def get_budget_keyboard():
    builder = ReplyKeyboardBuilder()
    for budget in BUDGETS:
        builder.add(KeyboardButton(text=budget))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_tones_keyboard():
    builder = ReplyKeyboardBuilder()
    for tone in TONES:
        builder.add(KeyboardButton(text=tone))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_zones_keyboard():
    builder = ReplyKeyboardBuilder()
    for zone in ZONES:
        builder.add(KeyboardButton(text=zone))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_people_keyboard():
    builder = ReplyKeyboardBuilder()
    for count in PEOPLE_COUNTS:
        builder.add(KeyboardButton(text=count))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_lighting_keyboard():
    builder = ReplyKeyboardBuilder()
    for light in LIGHTINGS:
        builder.add(KeyboardButton(text=light))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_furniture_keyboard():
    builder = ReplyKeyboardBuilder()
    for furniture in FURNITURE_LIST:
        builder.add(KeyboardButton(text=furniture))
    builder.add(KeyboardButton(text="свой вариант"))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_tech_keyboard():
    builder = ReplyKeyboardBuilder()
    for tech in TECH_LIST:
        builder.add(KeyboardButton(text=tech))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_materials_keyboard():
    builder = ReplyKeyboardBuilder()
    for material in MATERIALS:
        builder.add(KeyboardButton(text=material))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

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

def get_pets_keyboard():
    builder = ReplyKeyboardBuilder()
    for pet in PETS:
        builder.add(KeyboardButton(text=pet))
    builder.add(KeyboardButton(text="❌ Отменить"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

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

def get_photos_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="✅ ГОТОВО"))
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

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
        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
    )
    
    # Отправляем уведомление админам с кнопками
    for admin_id in ADMIN_IDS:
        try:
            await notify_admin(admin_id, request_id, message.from_user.id, answers, photos)
        except:
            pass
    
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
    
    # Отправляем фото
    for i, photo_id in enumerate(photos[:3], 1):
        await bot.send_photo(admin_id, photo_id, caption=f"Фото {i}")
    
    # Отправляем инлайн-кнопки для ответа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить на заявку", callback_data=f"reply_{request_id}")],
        [InlineKeyboardButton(text="✅ Отметить выполненной", callback_data=f"complete_{request_id}")]
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
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа!")
        return
    await message.answer("👑 АДМИН ПАНЕЛЬ\nВыберите действие:", reply_markup=get_admin_keyboard())

@dp.message(F.text == "🆕 Новые заявки")
async def view_new_requests(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    requests = get_all_requests(status='pending')
    
    if not requests:
        await message.answer("📭 Новых заявок нет.")
        return
    
    await message.answer(f"📭 НОВЫЕ ЗАЯВКИ ({len(requests)} шт.)\n━━━━━━━━━━━━━━━━━━━━")
    
    for req in requests:
        req_id, user_id, status, created_at = req
        full_req = get_request_by_id(req_id)
        answers = json.loads(full_req[4])
        photos = json.loads(full_req[5])
        
        text = format_request_for_admin(req_id, user_id, status, created_at, answers)
        await message.answer(text)
        
        for i, photo_id in enumerate(photos[:3], 1):
            await bot.send_photo(message.chat.id, photo_id, caption=f"Фото {i}")
        
        # Кнопки для заявки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_{req_id}")],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"complete_{req_id}")]
        ])
        await message.answer(f"Действия с заявкой #{req_id}:", reply_markup=keyboard)

@dp.message(F.text == "📋 Все заявки")
async def view_all_requests_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
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
    
    text += "\n━━━━━━━━━━━━━━━━━━━━\nДля просмотра заявки нажмите на её номер (пока не реализовано) или используйте поиск"
    await message.answer(text)
    
    # Предлагаем ввести ID заявки для просмотра
    await message.answer("Введите ID заявки для просмотра подробностей (например: 123):", reply_markup=get_cancel_keyboard())
    await AdminState.waiting_for_reply_text  # Временно используем это состояние

@dp.message(F.text == "📢 Рассылка")
async def broadcast_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("📢 Введите текст для рассылки всем пользователям:", reply_markup=get_cancel_keyboard())
    await AdminState.waiting_for_broadcast.set()

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
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Выход из админ-панели.", reply_markup=get_main_keyboard(True))

# ========== ИНЛАЙН-КНОПКИ ДЛЯ АДМИНОВ ==========
@dp.callback_query(lambda c: c.data and c.data.startswith('reply_'))
async def reply_to_request(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split('_')[1])
    await state.update_data(reply_request_id=request_id)
    
    await callback.message.answer(f"✍️ Введите текст ответа для заявки #{request_id}:\n(можно сразу отправлять фото, текст будет добавлен к фото)", reply_markup=get_cancel_keyboard())
    await callback.answer()
    await AdminState.waiting_for_reply_text.set()

@dp.callback_query(lambda c: c.data and c.data.startswith('complete_'))
async def complete_request(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split('_')[1])
    update_request_status(request_id, 'completed')
    
    # Получаем данные пользователя
    req = get_request_by_id(request_id)
    if req:
        user_id = req[1]
        await bot.send_message(user_id, f"✅ Ваша заявка #{request_id} отмечена как выполненная! Скоро получите результат.")
    
    await callback.message.edit_text(f"✅ Заявка #{request_id} отмечена как выполненная!")
    await callback.answer()

@dp.message(AdminState.waiting_for_reply_text)
async def process_reply_to_user(message: types.Message, state: FSMContext):
    if message.text and message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Отмена.", reply_markup=get_admin_keyboard())
        return
    
    data = await state.update_data()
    request_id = data.get('reply_request_id')
    
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
    
    # Обновляем статус
    update_request_status(request_id, 'completed')
    
    # Отправляем ответ пользователю
    if message.photo:
        # Если админ отправил фото с подписью
        photo_id = message.photo[-1].file_id
        caption = f"🏠 ВАШ ДИЗАЙН-ПРОЕКТ ГОТОВ!\n\nЗаявка #{request_id}\n\n{reply_text}\n\nСпасибо, что выбрали «Будущий дом»!"
        await bot.send_photo(user_id, photo_id, caption=caption)
    elif message.document:
        # Если отправили файл
        await bot.send_document(user_id, message.document.file_id, caption=reply_text)
    else:
        # Просто текст
        await bot.send_message(user_id, f"🏠 ВАШ ДИЗАЙН-ПРОЕКТ ГОТОВ!\n\nЗаявка #{request_id}\n\n{reply_text}\n\nСпасибо, что выбрали «Будущий дом»!")
    
    await message.answer(f"✅ Ответ отправлен пользователю!\nЗаявка #{request_id} закрыта.", reply_markup=get_admin_keyboard())
    await state.clear()

# ========== ОТМЕНА И ВСПОМОГАТЕЛЬНОЕ ==========
@dp.message(F.text == "❌ Отменить")
async def cancel_order(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and 'AdminState' in current_state:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_admin_keyboard())
    else:
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS))

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
