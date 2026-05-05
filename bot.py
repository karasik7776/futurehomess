import asyncio
import sqlite3
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import logging

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "ТВОЙ_ТОКЕН_БОТА"  # Замени на свой токен от @BotFather
ADMIN_IDS = [123456789]  # Замени на свой Telegram ID

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
FURNITURE_LIST = ['диван', 'кровать', 'шкаф', 'стол', 'стулья', 'стеллажи', 'пуф', 'телевизор', 'журнальный столик', 'комод']
TECH_LIST = ['холодильник', 'стиральная машина', 'кондиционер', 'камин', 'проектор', 'посудомоечная машина', 'духовка']
MATERIALS = ['да, предпочту дерево/натуральные ткани', 'нет, не принципиально']
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
    ready = State()
    photos = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
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

def get_pending_requests():
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, created_at, answers FROM requests WHERE status = 'pending' ORDER BY created_at DESC
    ''')
    requests = cursor.fetchall()
    conn.close()
    return requests

def get_all_requests():
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, status, created_at FROM requests ORDER BY created_at DESC
    ''')
    requests = cursor.fetchall()
    conn.close()
    return requests

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(is_admin=False):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🏠 Новый заказ"))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    if is_admin:
        builder.add(KeyboardButton(text="👑 Админ-панель"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📊 Новые заявки"))
    builder.add(KeyboardButton(text="📜 Все заявки"))
    builder.add(KeyboardButton(text="📢 Рассылка"))
    builder.add(KeyboardButton(text="◀️ В главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

# ========== ОТОБРАЖЕНИЕ АНКЕТЫ ==========
def format_answers(answers):
    text = "📋 <b>Ваша анкета:</b>\n\n"
    for key, value in answers.items():
        if value and key != 'photos':
            text += f"• <b>{key}</b>: {value}\n"
    return text

# ========== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username, 
              message.from_user.first_name, message.from_user.last_name)
    
    welcome_text = """
🏠 <b>Добро пожаловать в бот "Будущий дом"!</b>

Я помогу вам создать дизайн-проект вашей комнаты с помощью нейросети.

<b>📌 Как работать с ботом:</b>
1. Нажмите «Новый заказ»
2. Ответьте на вопросы о вашем идеальном интерьере
3. Загрузите 1-3 фото вашей комнаты
4. Наши дизайнеры обработают заявку и пришлют вам результат

<b>💡 Советы:</b>
• Отвечайте максимально подробно
• Фото должны быть при хорошем освещении
• Вы всегда можете отменить заказ кнопкой «Отменить»

Приятного использования! 🎨
"""
    
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_admin))

@dp.message(F.text == "ℹ️ Помощь")
async def show_help(message: types.Message):
    help_text = """
<b>❓ Помощь по боту "Будущий дом"</b>

<b>Команды:</b>
/start - Перезапустить бота
/cancel - Отменить текущий заказ

<b>Как создать заказ:</b>
1. Нажмите «Новый заказ»
2. Последовательно отвечайте на вопросы
3. В конце загрузите фото комнаты

<b>Где посмотреть статус заказа?</b>
Нажмите «Мои заказы» в главном меню

<b>Что делать, если я ошибся?</b>
Вы можете отменить заказ кнопкой «Отменить» и начать заново

<b>Связь с поддержкой:</b>
@support_username
"""
    await message.answer(help_text, parse_mode="HTML")

@dp.message(F.text == "🏠 Новый заказ")
async def new_order(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(answers={})
    await message.answer(
        "🛋️ <b>Давайте создадим дизайн вашей мечты!</b>\n\n"
        "Выберите, какую комнату хотите оформить:",
        reply_markup=get_room_keyboard(),
        parse_mode="HTML"
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
        await message.answer("Пожалуйста, выберите комнату из списка:", reply_markup=get_room_keyboard())
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
        await message.answer("Пожалуйста, выберите площадь из списка:", reply_markup=get_size_keyboard())
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
        await message.answer("Пожалуйста, выберите количество окон из списка:", reply_markup=get_windows_keyboard())
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
        await message.answer("Пожалуйста, выберите стиль из списка:", reply_markup=get_style_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Стиль"] = message.text
    await state.update_data(answers=answers)
    
    await ask_mood(message, state)

async def ask_mood(message: types.Message, state: FSMContext):
    await message.answer("😊 Какое настроение вы хотите создать?", reply_markup=get_mood_keyboard())
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
        await message.answer("Пожалуйста, выберите настроение из списка:", reply_markup=get_mood_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Настроение"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("💰 Есть ли бюджетные ограничения?", reply_markup=get_budget_keyboard())
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
    
    await message.answer("💰 Есть ли бюджетные ограничения?", reply_markup=get_budget_keyboard())
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
        await message.answer("Пожалуйста, выберите бюджет из списка:", reply_markup=get_budget_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Бюджет"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("🎨 Какие цвета вы хотите видеть в интерьере?\n(можно перечислить через запятую)", 
                        reply_markup=get_cancel_keyboard())
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
    
    await message.answer("🚫 Какие цвета вы НЕ хотите использовать?\n(можно пропустить, написав 'нет')", 
                        reply_markup=get_cancel_keyboard())
    await state.set_state(InteriorForm.colors_not_want)

@dp.message(InteriorForm.colors_not_want)
async def process_colors_not_want(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await cancel_order(message, state)
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Нежелательные цвета"] = message.text if message.text != "нет" else "нет"
    await state.update_data(answers=answers)
    
    await message.answer("🌓 Вы предпочитаете светлые или тёмные тона?", reply_markup=get_tones_keyboard())
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
        await message.answer("Пожалуйста, выберите тона из списка:", reply_markup=get_tones_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Тона"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("📍 Какие зоны должны быть в комнате?\n(можно выбрать несколько через запятую)", 
                        reply_markup=get_zones_keyboard())
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
        await message.answer("✏️ Напишите, какие зоны нужны:", reply_markup=get_cancel_keyboard())
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
        await message.answer("Пожалуйста, выберите количество из списка:", reply_markup=get_people_keyboard())
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
        await message.answer("Пожалуйста, выберите тип освещения из списка:", reply_markup=get_lighting_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Освещение"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("🛋️ Какая мебель обязательно должна быть?\n(выберите через запятую)", 
                        reply_markup=get_furniture_keyboard())
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
    
    await message.answer("📱 Есть ли крупная техника, которую нужно вписать?\n(выберите через запятую или напишите 'нет')", 
                        reply_markup=get_tech_keyboard())
    await state.set_state(InteriorForm.tech)

def get_tech_keyboard():
    builder = ReplyKeyboardBuilder()
    for tech in TECH_LIST:
        builder.add(KeyboardButton(text=tech))
    builder.add(KeyboardButton(text="нет"))
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
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_materials_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Экоматериалы"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("🐕 Есть ли домашние питомцы?", reply_markup=get_pets_keyboard())
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
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_pets_keyboard())
        return
    
    data = await state.update_data()
    answers = data.get("answers", {})
    answers["Питомцы"] = message.text
    await state.update_data(answers=answers)
    
    await message.answer("😞 Что вам категорически не нравится в текущем интерьере?\n(напишите текстом)", 
                        reply_markup=get_cancel_keyboard())
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
    
    await message.answer("❤️ Что вы хотели бы сохранить из текущей обстановки?\n(например, любимое кресло, картину, ковёр или напишите 'ничего')", 
                        reply_markup=get_cancel_keyboard())
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
    
    # Показываем итоговую анкету
    answers_text = format_answers(answers)
    await message.answer(
        f"{answers_text}\n\n"
        "🖼️ Теперь загрузите фотографии вашей комнаты (от 1 до 3 фото).\n"
        "Просто отправьте фото одно за другим.\n"
        "Когда закончите, нажмите «Готово»",
        parse_mode="HTML",
        reply_markup=get_photos_keyboard()
    )
    await state.set_state(InteriorForm.photos)
    await state.update_data(photos=[])

def get_photos_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="✅ Готово"))
    builder.add(KeyboardButton(text="❌ Отменить"))
    return builder.as_markup(resize_keyboard=True)

@dp.message(InteriorForm.photos, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.update_data()
    photos = data.get("photos", [])
    
    if len(photos) >= 3:
        await message.answer("Вы уже загрузили 3 фото. Нажмите «Готово», чтобы завершить.")
        return
    
    # Сохраняем file_id фото
    photo_file_id = message.photo[-1].file_id
    photos.append(photo_file_id)
    await state.update_data(photos=photos)
    
    remaining = 3 - len(photos)
    await message.answer(f"✅ Фото загружено! Осталось {remaining} фото. Или нажмите «Готово».")

@dp.message(InteriorForm.photos, F.text == "✅ Готово")
async def finish_photos(message: types.Message, state: FSMContext):
    data = await state.update_data()
    photos = data.get("photos", [])
    answers = data.get("answers", {})
    
    if len(photos) == 0:
        await message.answer("❌ Пожалуйста, загрузите хотя бы одно фото комнаты!")
        return
    
    answers["Количество фото"] = len(photos)
    
    # Сохраняем заявку в БД
    request_id = save_request(message.from_user.id, answers, photos)
    
    # Отправляем уведомление пользователю
    await message.answer(
        "✅ <b>Заявка успешно создана!</b>\n\n"
        f"🎫 Номер заявки: #{request_id}\n"
        "Статус: <b>Обрабатывается</b>\n\n"
        "Наши дизайнеры скоро приступят к работе над вашим проектом.\n"
        "Результат придет в этот чат. Спасибо, что выбрали «Будущий дом»! 🏠",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
    )
    
    # Отправляем уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            await notify_admin(admin_id, request_id, message.from_user.id, answers, photos)
        except:
            pass
    
    await state.clear()

@dp.message(InteriorForm.photos)
async def invalid_photos(message: types.Message, state: FSMContext):
    await message.answer("📸 Пожалуйста, отправьте фотографию комнаты или нажмите «Готово»", 
                        reply_markup=get_photos_keyboard())

async def notify_admin(admin_id, request_id, user_id, answers, photos):
    text = f"""
🔔 <b>Новая заявка #{request_id}</b>

👤 Пользователь: <code>{user_id}</code>
🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

<b>Параметры:</b>
{format_answers(answers)}

📸 Фото: {len(photos)} шт.

💡 Чтобы ответить пользователю, используйте команду:
/answer_{request_id} Текст ответа
"""
    await bot.send_message(admin_id, text, parse_mode="HTML")
    
    # Отправляем фото
    for i, photo_id in enumerate(photos[:3], 1):
        await bot.send_photo(admin_id, photo_id, caption=f"Фото {i}")

# ========== МОИ ЗАКАЗЫ ==========
@dp.message(F.text == "📋 Мои заказы")
async def my_orders(message: types.Message):
    conn = sqlite3.connect('future_home.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, status, created_at FROM requests WHERE user_id = ? ORDER BY created_at DESC
    ''', (message.from_user.id,))
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        await message.answer("📭 У вас пока нет заявок. Нажмите «Новый заказ», чтобы создать первую!")
        return
    
    text = "📋 <b>Ваши заявки:</b>\n\n"
    for order in orders:
        status_emoji = "🟡" if order[1] == "pending" else "🟢"
        text += f"{status_emoji} #{order[0]} - {order[1]} ({order[2][:10]})\n"
    
    await message.answer(text, parse_mode="HTML")

# ========== АДМИНСКИЕ ФУНКЦИИ ==========
@dp.message(F.text == "👑 Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админ-панели!")
        return
    
    await message.answer("👑 <b>Админ-панель</b>\nВыберите действие:", 
                        parse_mode="HTML", reply_markup=get_admin_keyboard())

@dp.message(F.text == "📊 Новые заявки")
async def view_new_requests(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    requests = get_pending_requests()
    
    if not requests:
        await message.answer("📭 Нет новых заявок.")
        return
    
    for req in requests:
        req_id, user_id, created_at, answers_json = req
        answers = json.loads(answers_json)
        
        text = f"""
🎫 <b>Заявка #{req_id}</b>
👤 Пользователь: <code>{user_id}</code>
🕐 Создана: {created_at[:19]}

{format_answers(answers)}

<b>Действия:</b>
/answer_{req_id} Текст ответа - отправить результат
"""
        await message.answer(text, parse_mode="HTML")
        
        # Получаем фото
        conn = sqlite3.connect('future_home.db')
        cursor = conn.cursor()
        cursor.execute('SELECT photos FROM requests WHERE id = ?', (req_id,))
        photos_json = cursor.fetchone()[0]
        conn.close()
        
        photos = json.loads(photos_json)
        for i, photo_id in enumerate(photos[:3], 1):
            await bot.send_photo(message.chat.id, photo_id, caption=f"Фото {i}")

@dp.message(F.text == "📜 Все заявки")
async def view_all_requests(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    requests = get_all_requests()
    
    if not requests:
        await message.answer("📭 Нет заявок в базе.")
        return
    
    text = "📋 <b>Все заявки:</b>\n\n"
    for req in requests:
        req_id, user_id, status, created_at = req
        status_emoji = "🟡" if status == "pending" else "🟢"
        text += f"{status_emoji} #{req_id} | {user_id} | {status} | {created_at[:10]}\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📢 Рассылка")
async def broadcast_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("📢 Введите текст для массовой рассылки всем пользователям:", 
                        reply_markup=get_cancel_keyboard())
    await state.set_state("broadcast")

@dp.message(StateFilter("broadcast"))
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
    
    success = 0
    fail = 0
    
    await message.answer(f"🚀 Начинаю рассылку {len(users)} пользователям...")
    
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 <b>Объявление</b>\n\n{message.text}", parse_mode="HTML")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await message.answer(f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {fail}", 
                        reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "◀️ В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Возврат в главное меню.", 
                        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS))

# ========== ОТВЕТ ПОЛЬЗОВАТЕЛЮ ОТ АДМИНА ==========
@dp.message(lambda msg: msg.text and msg.text.startswith('/answer_'))
async def answer_to_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа")
        return
    
    try:
        parts = message.text.split(' ', 1)
        request_id = int(parts[0].replace('/answer_', ''))
        response_text = parts[1] if len(parts) > 1 else "Ваш дизайн-проект готов!"
        
        # Получаем user_id из заявки
        conn = sqlite3.connect('future_home.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM requests WHERE id = ?', (request_id,))
        result = cursor.fetchone()
        
        if result:
            user_id = result[0]
            update_request_status(request_id, 'completed')
            
            # Отправляем ответ пользователю
            await bot.send_message(
                user_id,
                f"🎉 <b>Ваш дизайн-проект готов!</b>\n\n"
                f"Заявка #{request_id}\n\n"
                f"{response_text}\n\n"
                f"Спасибо, что выбрали «Будущий дом»! 🏠",
                parse_mode="HTML"
            )
            
            await message.answer(f"✅ Ответ отправлен пользователю (заявка #{request_id})")
            
            # Проверяем, нужно ли отправить фото
            if message.reply_to_message and message.reply_to_message.photo:
                await bot.send_photo(user_id, message.reply_to_message.photo[-1].file_id, 
                                    caption="🎨 Вот ваш дизайн-проект!")
        else:
            await message.answer("❌ Заявка не найдена")
        
        conn.close()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ========== ОТМЕНА ==========
@dp.message(F.text == "❌ Отменить")
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Действие отменено.\nВозврат в главное меню.",
        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await cancel_order(message, state)

# ========== ЗАПУСК БОТА ==========
async def main():
    init_db()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())