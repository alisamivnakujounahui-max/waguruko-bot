import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions

# --- СЕРВЕР ДЛЯ КРОНА ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Engine 8.0 Live!"
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
        user_data[uid] = {"name": name, "exp": 0, "cake": 0, "last_cake": 0, "warns": 0}
    if uid == OWNER_ID:
        user_data[uid]["exp"] = 999999

# --- УМНОЕ МЕНЮ ---
def get_main_menu(uid):
    kb = [
        [InlineKeyboardButton(text="🎭 РП Список", callback_data="rp_list"),
         InlineKeyboardButton(text="🍰 Скушать тортик", callback_data="eat_cake")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile"),
         InlineKeyboardButton(text="🏆 Топ тортиков", callback_data="cake_top")]
    ]
    # Показываем админку только избранным
    if uid in admins or uid == OWNER_ID:
        kb.append([InlineKeyboardButton(text="👑 Любимчики", callback_data="show_admins"),
                   InlineKeyboardButton(text="🛡 Админка", callback_data="admin_help")])
    
    kb.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРАБОТЧИКИ ---

@dp.callback_query(F.data == "eat_cake")
async def cake_logic(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_cake"] < 3600: # Раз в час
        return await call.answer("🔧 Животик еще полон! Подожди часик.", show_alert=True)
    
    change = random.randint(-5, 15)
    user_data[uid]["cake"] += change
    user_data[uid]["last_cake"] = now
    
    msg = f"🍰 Ты скушал кусочек тортика!\nРезультат: <b>{'+' if change > 0 else ''}{change} см</b>\nОбщий размер: <b>{user_data[uid]['cake']} см</b>"
    await call.message.edit_text(msg, parse_mode="HTML", reply_markup=get_main_menu(uid))

@dp.callback_query(F.data == "cake_top")
async def show_cake_top(call: CallbackQuery):
    sorted_cakes = sorted(user_data.items(), key=lambda x: x[1].get('cake', 0), reverse=True)[:10]
    text = "<b>🍰 Топ любителей тортиков:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_cakes, 1):
        text += f"{i}. {data['name']} — {data.get('cake', 0)} см\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu(call.from_user.id))

@dp.callback_query(F.data == "show_admins")
async def call_admins(call: CallbackQuery):
    text = "<b>👑 Любимчики Каоруко:</b>\n\n"
    for adm_id in admins:
        name = user_data.get(adm_id, {}).get("name", f"Юзер {adm_id}")
        text += f"• {name}\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu(call.from_user.id))

@dp.callback_query(F.data == "my_profile")
async def profile_call(call: CallbackQuery):
    uid = call.from_user.id
    check_user(uid, call.from_user.first_name)
    u = user_data[uid]
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in admins else "👤 Участник")
    res = f"<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n💠 <b>EXP:</b> {u['exp']}\n🎖 <b>Роль:</b> {role}\n🍰 <b>Тортик:</b> {u['cake']} см"
    await call.message.edit_text(res, parse_mode="HTML", reply_markup=get_main_menu(uid))

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: CallbackQuery): await call.message.delete()

# --- ПРИВЕТСТВИЕ С ГИФКОЙ ---
@dp.message(F.text.casefold().in_({"приветик вагури", "вагури меню", "меню"}))
async def msg_menu(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    # Прямая ссылка на гифку с Вагури (замени если есть другая)
    gif_url = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHJueXF6bmZ6bmZ6bmZ6bmZ6bmZ6bmZ6bmZ6bmZ6bmZ6bmZ6JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxxcaOXYT60/giphy.gif"
    
    caption = f"<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\nПриветик! Я тут. Что будем делать сегодня?"
    if uid == OWNER_ID:
        caption = f"<b>『 🌸 𝓦𝓪𝓰𝓾𝓻𝓲𝓴𝓸 』</b>\n\nЗдравствуй, мой любимый Создатель! ❤️ Я готова к работе."

    await m.answer_animation(gif_url, caption=caption, parse_mode="HTML", reply_markup=get_main_menu(uid))

# --- РП И АДМИНКА ---
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
        return await m.answer(f"🛡 {m.reply_to_message.from_user.first_name} теперь в списке любимчиков!")

    if txt == "мут" and is_adm and m.reply_to_message:
        await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=10))
        return await m.answer("🤫 Тишина в библиотеке! Мут на 10 минут.")

    # (Тут можно добавить остальные РП команды по аналогии)

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())