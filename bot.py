import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions

# --- СЕРВЕР ДЛЯ КРОНА ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Engine 7.5: Cake System Online!"
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
        user_data[uid] = {
            "name": name, "exp": 0, "cake": 0, 
            "last_cake": 0, "last_date": 0, "warns": 0
        }

# --- УМНОЕ МЕНЮ ---
def main_menu(uid):
    kb = [
        [InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"),
         InlineKeyboardButton(text="🍰 Скушать тортик", callback_data="eat_cake")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="🏆 Топ тортиков", callback_data="cake_top")],
        [InlineKeyboardButton(text="❤️ Свидание", callback_data="go_date"),
         InlineKeyboardButton(text="📊 Топ EXP", callback_data="show_top")]
    ]
    # Админские кнопки только для своих
    if uid in admins or uid == OWNER_ID:
        kb.append([InlineKeyboardButton(text="👑 Любимчики", callback_data="show_admins"),
                   InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")])
    
    kb.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРАБОТЧИКИ ТОРТИКОВ ---

@dp.callback_query(F.data == "eat_cake")
async def cake_logic(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    now = time.time()
    
    if now - user_data[uid]["last_cake"] < 3600: # Раз в час
        return await call.answer("⏳ Животик еще полон! Попробуй через часик.", show_alert=True)
    
    change = random.randint(-5, 15)
    user_data[uid]["cake"] += change
    user_data[uid]["last_cake"] = now
    
    res = f"🍰 Ты скушал кусочек тортика! Твой результат: <b>{'+' if change > 0 else ''}{change} см</b>.\nТеперь твой тортик: <b>{user_data[uid]['cake']} см</b>!"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(uid))

@dp.callback_query(F.data == "cake_top")
async def cake_top_call(call: CallbackQuery):
    sorted_cakes = sorted(user_data.items(), key=lambda x: x[1].get('cake', 0), reverse=True)[:10]
    text = "<b>🍰 Таблица любителей тортиков:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_cakes, 1):
        text += f"{i}. {data['name']} — {data.get('cake', 0)} см\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

# --- ОСТАЛЬНЫЕ ОБРАБОТЧИКИ (СТАБИЛЬНЫЕ) ---

@dp.callback_query(F.data == "my_profile")
async def profile_call(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in admins else "👤 Участник")
    res = f"<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\n👤 <b>Профиль:</b> {u['name']}\n💠 <b>EXP:</b> {u['exp']}\n🍰 <b>Тортик:</b> {u['cake']} см\n🎖 <b>Роль:</b> {role}"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=main_menu(uid))

@dp.callback_query(F.data == "show_admins")
async def call_admins(call: CallbackQuery):
    text = "<b>👑 Любимчики Каоруко:</b>\n\n"
    for adm_id in admins:
        name = user_data.get(adm_id, {}).get("name", f"Юзер {adm_id}")
        text += f"• {name}\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: CallbackQuery): await call.message.delete()

# --- РП ДЕЙСТВИЯ ---
rp_actions = {
    "обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "вьебать": "slap",
    "лик": "lick", "сон": "sleep", "танец": "dance", "ням": "nom", "чмок": "smile",
    "игра": "poke", "секс": "spank", "щекотка": "tickle", "массаж": "pat",
    "гладить": "pat"
}

@dp.message(F.text.casefold().in_({"меню", "приветик вагури"}))
async def msg_menu(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    await m.answer("<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\nЯ тут! Что хочешь посмотреть?", parse_mode="HTML", reply_markup=main_menu(uid))

@dp.message()
async def handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    is_adm = uid in admins or uid == OWNER_ID

    if txt == "+админ" and uid == OWNER_ID and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        if tid not in admins: admins.append(tid)
        return await m.answer(f"🛡 {m.reply_to_message.from_user.first_name} теперь админ!")

    if txt in rp_actions and m.reply_to_message:
        target = m.reply_to_message.from_user.mention_html()
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.waifu.pics/sfw/{rp_actions[txt]}") as r:
                url = (await r.json())["url"] if r.status == 200 else None
                msg = f"『 🌸 』 {m.from_user.mention_html()} сделал(а) <b>{txt}</b> для {target}"
                if url: await m.answer_animation(url, caption=msg, parse_mode="HTML")
                else: await m.answer(msg, parse_mode="HTML")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())