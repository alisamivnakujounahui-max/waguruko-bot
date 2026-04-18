import asyncio, random, aiohttp, time, os, json
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions

# --- СЕРВЕР ДЛЯ КРОНА ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Engine 10.0: Persistent Memory Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СИСТЕМА ПАМЯТИ (JSON DB) ---
DB_FILE = "db.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "admins": [OWNER_ID]}

def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db = load_data()
user_data = db["users"]
admins = db["admins"]

def check_user(uid, name):
    uid_str = str(uid)
    if uid_str not in user_data:
        user_data[uid_str] = {"name": name, "exp": 0, "cake": 0, "last_cake": 0, "last_date": 0, "warns": 0}
        save_data()

# --- КЛАВИАТУРА ---
def main_menu(uid):
    uid_int = int(uid)
    kb = [
        [InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"),
         InlineKeyboardButton(text="🍰 Скушать тортик", callback_data="eat_cake")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="👑 Любимчики", callback_data="show_admins")],
        [InlineKeyboardButton(text="❤️ Свидание", callback_data="go_date"),
         InlineKeyboardButton(text="🏆 Топ тортиков", callback_data="cake_top")],
        [InlineKeyboardButton(text="📊 Топ EXP", callback_data="show_top")]
    ]
    if uid_int in admins or uid_int == OWNER_ID:
        kb.append([InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")])
    
    kb.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРАБОТЧИКИ CALLBACK (КНОПКИ) ---

@dp.callback_query(F.data == "rp_list")
async def call_rp_list(call: CallbackQuery):
    text = "<b>🎭 РП:</b> обнять, поцеловать, кусь, вьебать, лик, сон, танец, ням, чмок, игра, секс, щекотка, массаж, ванна, подарок, гладить..."
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "eat_cake")
async def call_eat_cake(call: CallbackQuery):
    uid = str(call.from_user.id)
    check_user(uid, call.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_cake"] < 3600:
        return await call.answer("⏳ Ты еще не проголодался!", show_alert=True)
    
    grow = random.randint(0, 15)
    user_data[uid]["cake"] += grow
    user_data[uid]["last_cake"] = now
    save_data()
    res = f"🍰 Тортик вырос на <b>{grow} см</b>!\nВсего: <b>{user_data[uid]['cake']} см</b>"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "go_date")
async def call_date(call: CallbackQuery):
    uid = str(call.from_user.id)
    check_user(uid, call.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_date"] < 14400:
        return await call.answer("⏳ Вагури отдыхает!", show_alert=True)
    
    user_data[uid]["last_date"] = now
    bonus = random.choice([25, -5])
    user_data[uid]["exp"] += bonus
    save_data()
    res = f"❤️ Свидание принесло <b>{bonus} EXP</b>!"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "my_profile")
async def call_profile(call: CallbackQuery):
    uid = str(call.from_user.id)
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if int(uid) == OWNER_ID else ("🛡 Админ" if int(uid) in admins else "👤 Участник")
    res = f"<b>『 🌸 Профиль 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n💠 <b>EXP:</b> {u['exp']}\n🍰 <b>Тортик:</b> {u['cake']} см\n🎖 <b>Роль:</b> {role}"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "show_admins")
async def call_show_admins(call: CallbackQuery):
    text = "<b>👑 Любимчики:</b>\n\n"
    for a_id in admins:
        text += f"• ID: {a_id}\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "cake_top")
async def call_cake_top(call: CallbackQuery):
    top = sorted(user_data.items(), key=lambda x: x[1]['cake'], reverse=True)[:5]
    res = "<b>🍰 Топ Тортиков:</b>\n\n"
    for i, (uid, data) in enumerate(top, 1):
        res += f"{i}. {data['name']} — {data['cake']} см\n"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "show_top")
async def call_exp_top(call: CallbackQuery):
    top = sorted(user_data.items(), key=lambda x: x[1]['exp'], reverse=True)[:5]
    res = "<b>📊 Топ EXP:</b>\n\n"
    for i, (uid, data) in enumerate(top, 1):
        res += f"{i}. {data['name']} — {data['exp']} EXP\n"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "admin_help")
async def call_admin_help(call: CallbackQuery):
    await call.message.edit_text("<b>🛡 Команды:</b>\nмут, варн, бан, +админ", parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "close_menu")
async def call_close(call: CallbackQuery): await call.message.delete()

# --- ЛОГИКА СООБЩЕНИЙ ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    check_user(m.from_user.id, m.from_user.first_name)
    await m.answer("🌸 Приветик! Я Вагури Каоруко. Чтобы вызвать меню, просто позови меня по имени!", reply_markup=main_menu(m.from_user.id))

@dp.message(lambda m: any(w in m.text.lower() for w in ["вагури", "каоруко"]))
async def name_call(m: types.Message):
    if m.text.startswith("/"): return
    check_user(m.from_user.id, m.from_user.first_name)
    await m.answer(f"Звал меня, {m.from_user.first_name}? 😊", reply_markup=main_menu(m.from_user.id))

@dp.message()
async def main_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    
    # +админ (только для тебя)
    if txt == "+админ" and uid == OWNER_ID and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        if tid not in admins: 
            admins.append(tid)
            save_data()
        return await m.answer("🛡 Добавлен в любимчики!")

    # РП (упрощенно для стабильности)
    rps = ["обнять", "поцеловать", "кусь", "гладить", "ням"]
    if txt in rps and m.reply_to_message:
        user_data[str(uid)]["exp"] += 2
        save_data()
        await m.answer(f"🌸 {m.from_user.first_name} выполнил {txt}!")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())