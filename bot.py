import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Iris-Mode Active!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
OWNER_ID = 123456789 # !!! ЗАМЕНИ НА СВОЙ ID (узнай его через бот @userinfobot) !!!

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 
admins = [OWNER_ID] # Список тех, кто может модерировать

def check_user(uid, name):
    if uid not in user_data:
        user_data[uid] = {"name": name, "exp": 0, "partner": None, "warns": 0, "last_date": 0}

# --- КНОПКИ (МЕНЮ) ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🎭 РП Команды", callback_data="rp_list"),
         InlineKeyboardButton(text="❤️ Свидание", callback_data="go_date")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="🏆 Рейтинг", callback_data="show_top")],
        [InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ЛОГИКА ---

@dp.message(F.text.casefold() == "приветик вагури")
async def msg_menu(m: types.Message):
    await m.answer("🌸 Приветик! Я приготовила для тебя меню управления. Выбирай, что хочешь сделать:", reply_markup=main_menu())

@dp.callback_query(F.data == "rp_list")
async def rp_list(call: types.CallbackQuery):
    text = ("<b>🎭 Список РП:</b>\nобнять, кусь, ням, лик, сон, секс, гладить, злиться, грустить, "
            "радоваться, хвалить, обидеться, подмигнуть, испугаться, щекотка, массаж, ванна, подарок...")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "my_profile")
async def my_profile(call: types.CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in admins else "👤 Участник")
    res = f"👤 <b>Профиль:</b> {u['name']}\n💠 <b>EXP:</b> {u['exp']}\n🎖 <b>Роль:</b> {role}\n⚠️ <b>Варны:</b> {u['warns']}/3"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu())

# --- МОДЕРАЦИЯ ---

@dp.message(F.text.casefold().startswith("размут"))
async def unmute(m: types.Message):
    if m.from_user.id not in admins: return
    if not m.reply_to_message: return
    await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=True))
    await m.answer(f"✨ {m.reply_to_message.from_user.first_name} снова может говорить!")

@dp.message(F.text.casefold().startswith("снять варн"))
async def unwarn(m: types.Message):
    if m.from_user.id not in admins: return
    if not m.reply_to_message: return
    tid = m.reply_to_message.from_user.id
    check_user(tid, m.reply_to_message.from_user.first_name)
    if user_data[tid]["warns"] > 0: user_data[tid]["warns"] -= 1
    await m.answer(f"😇 С игрока {m.reply_to_message.from_user.first_name} снят один варн! ({user_data[tid]['warns']}/3)")

@dp.message(F.text.casefold().startswith("разбан"))
async def unban(m: types.Message):
    if m.from_user.id not in admins: return
    # Для разбана в ТГ обычно нужен ID, так как реплайнуть нельзя (человека нет в чате)
    # Но для простоты оставим логику админки ТГ
    await m.answer("Используй стандартный разбан Telegram, чтобы вернуть человека!")

@dp.message(F.text.casefold().startswith("+админ"))
async def add_admin(m: types.Message):
    if m.from_user.id != OWNER_ID: return
    if not m.reply_to_message: return
    tid = m.reply_to_message.from_user.id
    if tid not in admins: admins.append(tid)
    await m.answer(f"🛡 {m.reply_to_message.from_user.first_name} теперь мой помощник!")

# --- СТАНДАРТНЫЙ ОБРАБОТЧИК (РП) ---
# [Здесь остается логика РП из прошлого кода, чтобы не раздувать сообщение]
# ... (вставь сюда кусок @dp.message() с РП действиями) ...

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())