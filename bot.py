import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions

# --- СЕРВЕР-ЗАГЛУШКА ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Full Engine Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных
user_data = {} 

def check_user(uid, name):
    if uid not in user_data:
        user_data[uid] = {
            "name": name, "exp": 0, "partner": None, "m_req": None,
            "last_date": 0, "warns": 0, "stats": {"hugs": 0}
        }

# РП КОМАНДЫ (23 штуки)
rp_actions = {
    "обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "вьебать": "slap",
    "лик": "lick", "сон": "sleep", "танец": "dance", "ням": "nom",
    "чмок": "smile", "игра": "poke", "секс": "spank", "щекотка": "tickle",
    "массаж": "pat", "ванна": "cuddle", "подарок": "handhold",
    "гладить": "pat", "злиться": "bully", "грустить": "sad", "радоваться": "happy",
    "хвалить": "smile", "обидеться": "blush", "подмигнуть": "wink", "испугаться": "shrug"
}

rp_texts = {
    "обнять": "крепко обнимает {target} 🤗", "поцеловать": "нежно целует {target} 💋",
    "кусь": "делает кусь {target} 🦷", "вьебать": "дает смачного леща {target} 👊",
    "лик": "лижет щечку {target} 👅", "сон": "укрывает {target} одеялком ✨",
    "танец": "танцует с {target} 💃", "ням": "кормит {target} вкусняшкой 🍰",
    "чмок": "дарит чмок {target} 😊", "игра": "играет в приставку с {target} 🎮",
    "секс": "наказывает {target} 🔞", "щекотка": "щекочет {target} 😂",
    "массаж": "мнет плечики {target} 💆‍♂️", "ванна": "плещется в ванне с {target} 🛁",
    "подарок": "вручает подарок {target} 🎁", "гладить": "гладит по голове {target} 🥺",
    "злиться": "топает ножками на {target} 💢", "грустить": "плачет на плече у {target} 💧",
    "радоваться": "прыгает от счастья с {target} ✨", "хвалить": "хвалит {target} ⭐",
    "обидеться": "надул(а) губки на {target} 😤", "подмигнуть": "подмигивает {target} 😉",
    "испугаться": "прячется за {target} 🙀"
}

# Проверка на админа
async def is_admin(m: types.Message):
    member = await m.chat.get_member(m.from_user.id)
    return member.status in ["administrator", "creator"]

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer(f"🌸 Привет! Я Каоруко. Твой админ и друг.\nНапиши /help, чтобы увидеть всё!")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    await m.answer("<b>🛡 Админка:</b> мут, размут, варн, бан (реплаем)\n"
                   "<b>❤️ Любовь:</b> 'ты выйдешь за меня?', /date, /divorce\n"
                   "<b>👤 Инфо:</b> /profile, /top\n"
                   "<b>🎭 РП:</b> обнять, кусь, ням, лик, сон, секс, гладить и др. (всего 23)", parse_mode="HTML")

@dp.message(Command("date"))
async def cmd_date(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_date"] < 14400:
        return await m.reply("⏳ Каоруко отдыхает. Приходи попозже!")
    
    user_data[uid]["last_date"] = now
    if random.randint(1, 100) <= 60:
        user_data[uid]["exp"] += 20
        await m.answer_animation("https://i.waifu.pics/vN7E2E0.gif", caption="☀️ <b>Успех!</b> Свидание прошло чудесно!\n<b>+20 EXP</b>", parse_mode="HTML")
    else:
        user_data[uid]["exp"] -= 5
        await m.answer("🌧 Пошел дождь, и вы немного поспорили... ( -5 EXP )")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    u = user_data[uid]
    exp = u["exp"]
    if exp < 100: rank = "Незнакомец 👤"
    elif exp < 500: rank = "Друг 🌸"
    else: rank = "Родная душа 👑"
    
    await m.answer(f"👤 <b>Профиль:</b> {m.from_user.first_name}\n💠 <b>EXP:</b> {exp}\n🎭 <b>Статус:</b> {rank}\n⚠️ <b>Варны:</b> {u['warns']}/3", parse_mode="HTML")

@dp.message(F.new_chat_members)
async def welcome(m: types.Message):
    for u in m.new_chat_members:
        await m.answer(f"🌸 Привет, {u.first_name}! Каоруко рада тебя видеть! Пей чай и не хулигань.")

# --- МОДЕРАЦИЯ ---

@dp.message(F.text.casefold().startswith("мут"))
async def mute(m: types.Message):
    if not await is_admin(m): return
    if not m.reply_to_message: return await m.reply("Ответь на сообщение нарушителя!")
    try:
        await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=10))
        await m.answer(f"🤫 {m.reply_to_message.from_user.first_name} в углу на 10 минут.")
    except: await m.answer("Сделай меня админом!")

@dp.message(F.text.casefold().startswith("варн"))
async def warn(m: types.Message):
    if not await is_admin(m): return
    if not m.reply_to_message: return
    tid = m.reply_to_message.from_user.id
    check_user(tid, m.reply_to_message.from_user.first_name)
    user_data[tid]["warns"] += 1
    if user_data[tid]["warns"] >= 3:
        await m.chat.ban(tid)
        await m.answer(f"🚫 {m.reply_to_message.from_user.first_name} забанен за 3 варна!")
    else:
        await m.answer(f"⚠️ Предупреждение для {m.reply_to_message.from_user.first_name} ({user_data[tid]['warns']}/3)")

# --- ОБРАБОТЧИК ---

@dp.message()
async def handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)

    # Брак
    if txt == "ты выйдешь за меня?" and m.reply_to_message:
        tid = m.reply_to_message.from_user.id
        check_user(tid, m.reply_to_message.from_user.first_name)
        user_data[tid]["m_req"] = uid
        return await m.answer(f"💍 {m.reply_to_message.from_user.mention_html()}, ты согласна?", parse_mode="HTML")
    
    if txt == "согласен" and user_data[uid].get("m_req"):
        rid = user_data[uid]["m_req"]
        user_data[uid]["partner"], user_data[rid]["partner"] = rid, uid
        user_data[uid]["m_req"] = None
        return await m.answer("💖 Теперь вы пара!")

    # РП
    if txt in rp_actions and m.reply_to_message:
        target = m.reply_to_message.from_user.mention_html()
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.waifu.pics/sfw/{rp_actions[txt]}") as r:
                url = (await r.json())["url"] if r.status == 200 else None
                msg = f"{m.from_user.mention_html()} {rp_texts[txt].format(target=target)}"
                if url: await m.answer_animation(url, caption=msg, parse_mode="HTML")
                else: await m.answer(msg, parse_mode="HTML")
        user_data[uid]["exp"] += 2

async def main():
    keep_alive()
    await bot.set_my_commands([BotCommand(command="help", description="Помощь"), BotCommand(command="date", description="Свидание")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())