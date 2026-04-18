import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Engine 9.0: Logic Fixed!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 
admins = [OWNER_ID] 

def check_user(uid, name):
    if uid not in user_data:
        user_data[uid] = {"name": name, "exp": 0, "cake": 0, "last_cake": 0, "last_date": 0, "warns": 0}

# --- МЕНЮ (ЛЮБИМЧИКИ ТЕПЕРЬ ДЛЯ ВСЕХ) ---
def main_menu(uid):
    kb = [
        [InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"),
         InlineKeyboardButton(text="🍰 Скушать тортик", callback_data="eat_cake")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="👑 Любимчики", callback_data="show_admins")],
        [InlineKeyboardButton(text="❤️ Свидание", callback_data="go_date"),
         InlineKeyboardButton(text="🏆 Топ тортиков", callback_data="cake_top")],
        [InlineKeyboardButton(text="📊 Топ EXP", callback_data="show_top")]
    ]
    # Только кнопка админки скрыта для обычных
    if uid in admins or uid == OWNER_ID:
        kb.append([InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")])
    
    kb.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ЛОГИКА ТОРТИКА (БЕЗ МИНУСОВ) ---
@dp.callback_query(F.data == "eat_cake")
async def cake_logic(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    now = time.time()
    
    if now - user_data[uid]["last_cake"] < 3600:
        return await call.answer("⏳ Ты еще не проголодался! Заходи через часик.", show_alert=True)
    
    user_data[uid]["last_cake"] = now
    # Логика: тортик растет, но может "подгореть" (прибавить 0), в минус не уходит
    chance = random.randint(1, 100)
    if chance > 20: # 80% шанс успеха
        grow = random.randint(1, 12)
        user_data[uid]["cake"] += grow
        res = f"🧁 <b>Вкуснятина!</b>\nТвой тортик вырос на <b>{grow} см</b>.\nТеперь он: <b>{user_data[uid]['cake']} см</b>!"
    else: # 20% шанс, что тортик просто не вырос
        res = "☁️ <b>Ой!</b>\nТортик оказался невкусным и не вырос в размере. Попробуй позже!"
    
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(uid))

# --- КОМАНДА /START ---
@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    text = (
        "<b>『 🌸 Приветик! Я Вагури Каоруко 』</b>\n\n"
        "Я твоя верная помощница и душа этого чата! ✨\n\n"
        "<b>Что я умею:</b>\n"
        "🎭 <b>РП-действия:</b> Обнимашки, кусь и еще 20+ команд.\n"
        "🍰 <b>Тортики:</b> Кушай сладости и расти свой личный тортик!\n"
        "❤️ <b>Свидания:</b> Ухаживай за мной и копи опыт (EXP).\n"
        "🛡 <b>Порядок:</b> Помогаю админам следить за чатом.\n\n"
        "<i>Чтобы вызвать меню, просто позови меня по имени в любом сообщении!</i>"
    )
    await m.answer(text, parse_mode="HTML", reply_markup=main_menu(uid))

# --- ТРИГГЕР НА ИМЯ ---
@dp.message(lambda m: any(word in m.text.lower() for word in ["вагури", "каоруко"]))
async def name_trigger(m: types.Message):
    # Если это не просто команда /start
    if m.text.startswith("/"): return
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    await m.answer(f"<b>Кто-то звал Вагури?</b> 😊\nЧем могу помочь, {m.from_user.first_name}?", parse_mode="HTML", reply_markup=main_menu(uid))

# --- ОБРАБОТЧИКИ ОСТАЛЬНЫХ КНОПОК ---

@dp.callback_query(F.data == "show_admins")
async def call_admins(call: CallbackQuery):
    text = "<b>👑 Любимчики (Наши Админы):</b>\n\n"
    for adm_id in admins:
        name = user_data.get(adm_id, {}).get("name", f"Юзер {adm_id}")
        tag = "⭐ Создатель" if adm_id == OWNER_ID else "💎 Помощник"
        text += f"• {name} [{tag}]\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "my_profile")
async def profile_call(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in admins else "👤 Участник")
    res = f"<b>『 🌸 Профиль 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n💠 <b>EXP:</b> {u['exp']}\n🍰 <b>Тортик:</b> {u['cake']} см\n🎖 <b>Роль:</b> {role}"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(uid))

@dp.callback_query(F.data == "cake_top")
async def cake_top_call(call: CallbackQuery):
    sorted_cakes = sorted(user_data.items(), key=lambda x: x[1].get('cake', 0), reverse=True)[:10]
    text = "<b>🍰 Топ сладкоежек чата:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_cakes, 1):
        text += f"{i}. {data['name']} — {data['cake']} см\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: CallbackQuery): await call.message.delete()

# (Здесь остаются остальные обработчики: show_top, rp_list, admin_help, handler для РП и т.д.)

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())