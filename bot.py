import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Mega Engine 7.0 Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных
user_data = {} 
admins = [OWNER_ID] 

def check_user(uid, name):
    if uid not in user_data:
        user_data[uid] = {"name": name, "exp": 0, "partner": None, "m_req": None, "last_date": 0, "warns": 0}

# --- МЕНЮ (КНОПКИ) ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"),
         InlineKeyboardButton(text="❤️ Свидание", callback_data="go_date")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="👑 Любимчики", callback_data="show_admins")],
        [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="show_top"),
         InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРАБОТЧИКИ CALLBACK ---

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: CallbackQuery):
    await call.message.delete()

@dp.callback_query(F.data == "show_admins")
async def call_admins(call: CallbackQuery):
    text = "<b>👑 Любимчики Каоруко:</b>\n\n"
    for adm_id in admins:
        name = user_data.get(adm_id, {}).get("name", f"ID: {adm_id}")
        tag = "⭐ Создатель" if adm_id == OWNER_ID else "💎 Помощник"
        text += f"• <b>{name}</b> [{tag}]\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "rp_list")
async def rp_list_call(call: CallbackQuery):
    text = ("<b>🎭 РП Команды (реплаем):</b>\n"
            "обнять, поцеловать, кусь, вьебать, лик, сон, танец, ням, чмок, игра, секс, щекотка, массаж, ванна, подарок, гладить, злиться, грустить, радоваться, хвалить, обидеться, подмигнуть, испугаться")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "my_profile")
async def profile_call(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in admins else "👤 Участник")
    res = f"<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n💠 <b>Опыт:</b> {u['exp']}\n🎖 <b>Роль:</b> {role}\n⚠️ <b>Варны:</b> {u['warns']}/3"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "go_date")
async def date_call(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_date"] < 14400:
        return await call.answer("⏳ Каоруко еще занята! Приходи позже.", show_alert=True)
    user_data[uid]["last_date"] = now
    if random.randint(1, 100) <= 65:
        user_data[uid]["exp"] += 25
        await call.message.edit_text("🍰 <b>Успех!</b> Вы чудесно провели время в кафе.\n<b>+25 EXP</b>", parse_mode="HTML", reply_markup=main_menu())
    else:
        user_data[uid]["exp"] -= 5
        await call.message.edit_text("🌧 <b>Неудача...</b> Пошел дождь, и настроение испортилось.\n<b>-5 EXP</b>", parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "show_top")
async def top_call(call: CallbackQuery):
    if not user_data: return await call.answer("Топ пока пуст!")
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['exp'], reverse=True)[:5]
    top_text = "<b>🏆 Топ любимчиков:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        top_text += f"{i}. {data['name']} — {data['exp']} EXP\n"
    await call.message.edit_text(top_text, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "admin_help")
async def admin_help_call(call: CallbackQuery):
    text = ("<b>🛡 Команды админа (реплаем):</b>\n"
            "• <code>мут</code> / <code>размут</code>\n"
            "• <code>варн</code> / <code>снять варн</code>\n"
            "• <code>бан</code> / <code>разбан</code>\n"
            "• <code>+админ</code>")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())

# --- РП ДАННЫЕ ---
rp_actions = {
    "обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "вьебать": "slap",
    "лик": "lick", "сон": "sleep", "танец": "dance", "ням": "nom",
    "чмок": "smile", "игра": "poke", "секс": "spank", "щекотка": "tickle",
    "массаж": "pat", "ванна": "cuddle", "подарок": "handhold",
    "гладить": "pat", "злиться": "bully", "грустить": "sad", "радоваться": "happy",
    "хвалить": "smile", "обидеться": "blush", "подмигнуть": "wink", "испугаться": "shrug"
}

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@dp.message(F.text.casefold().in_({"приветик вагури", "вагури меню", "каоруко меню", "меню", "вагури привет"}))
async def cmd_open_menu(m: types.Message):
    await m.answer("<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\nЯ тут! Чем могу помочь?", parse_mode="HTML", reply_markup=main_menu())

@dp.message()
async def main_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    is_adm = uid in admins or uid == OWNER_ID

    # Админские команды
    if txt == "+админ" and uid == OWNER_ID and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        check_user(tid, m.reply_to_message.from_user.first_name)
        if tid not in admins: admins.append(tid)
        return await m.answer(f"🛡 {m.reply_to_message.from_user.first_name} теперь мой любимчик-помощник!")

    if txt == "мут" and is_adm and m.reply_to_message:
        await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=10))
        return await m.answer(f"🤫 {m.reply_to_message.from_user.first_name} отправлен в угол на 10 минут.")

    if txt == "размут" and is_adm and m.reply_to_message:
        await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=True))
        return await m.answer(f"✨ {m.reply_to_message.from_user.first_name} прощен!")

    if txt == "варн" and is_adm and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        check_user(tid, m.reply_to_message.from_user.first_name)
        user_data[tid]["warns"] += 1
        if user_data[tid]["warns"] >= 3:
            await m.chat.ban(tid)
            return await m.answer("🚫 3 варна! Прощай навсегда.")
        return await m.answer(f"⚠️ Предупреждение для {m.reply_to_message.from_user.first_name} ({user_data[tid]['warns']}/3)")

    if txt == "снять варн" and is_adm and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        check_user(tid, m.reply_to_message.from_user.first_name)
        if user_data[tid]["warns"] > 0: user_data[tid]["warns"] -= 1
        return await m.answer(f"😇 С {m.reply_to_message.from_user.first_name} снят варн!")

    # РП команды
    if txt in rp_actions and m.reply_to_message:
        target = m.reply_to_message.from_user.mention_html()
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.waifu.pics/sfw/{rp_actions[txt]}") as r:
                url = (await r.json())["url"] if r.status == 200 else None
                msg = f"『 🌸 』 {m.from_user.mention_html()} выполняет <b>{txt}</b> для {target}!"
                if url: await m.answer_animation(url, caption=msg, parse_mode="HTML")
                else: await m.answer(msg, parse_mode="HTML")
        user_data[uid]["exp"] += 2

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())