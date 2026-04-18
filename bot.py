import asyncio, random, aiohttp, time, os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Каоруко готова к свиданию!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 

def check_user(uid, name):
    if uid not in user_data:
        user_data[uid] = {
            "name": name, "exp": 0, "partner": None, "m_req": None,
            "last_date": 0, "stats": {"hugs": 0, "dates": 0}
        }

# Расширенные РП
rp_actions = {
    "обнять": {"t": "обнял(а) {target} 🤗", "g": "hug"},
    "кусь": {"t": "сделал(а) кусь {target} 🦷", "g": "bite"},
    "поцеловать": {"t": "поцеловал(а) {target} 💋", "g": "kiss"},
    "вьебать": {"t": "вьебал(а) {target} с ноги 👊", "g": "slap"},
    "лик": {"t": "лизнул(а) {target} 👅", "g": "lick"},
    "сон": {"t": "уложил(а) {target} спать ✨", "g": "sleep"},
    "танец": {"t": "кружится в танце с {target} 💃", "g": "dance"},
    "хавчик": {"t": "кормит {target} вкусняшками 🍰", "g": "nom"},
    "чмок": {"t": "чмокнул(а) в щечку {target} 😊", "g": "smile"},
    "игра": {"t": "играет с {target} 🎮", "g": "poke"},
    "секс": {"t": "занимается жестким сексом с {target} 🔞", "g": "spank"}
}

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="help", description="Все возможности"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="date", description="Свидание с Каоруко (1 раз в день)"),
        BotCommand(command="top", description="Топ чата"),
        BotCommand(command="divorce", description="Развод")
    ]
    await bot.set_my_commands(commands)

# --- ЛОГИКА ---

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    await m.answer("<b>❤️ Взаимодействие:</b>\n• Реплай: <i>'ты выйдешь за меня?'</i>\n• /date — свидание с Каоруко\n\n<b>🎭 РП команды:</b>\nобнять, кусь, поцеловать, вьебать, лик, сон, танец, хавчик, чмок, игра, секс", parse_mode="HTML")

@dp.message(Command("date"))
async def cmd_date(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    now = time.time()
    
    if now - user_data[uid]["last_date"] < 86400:
        rem = int((86400 - (now - user_data[uid]["last_date"])) / 3600)
        return await m.reply(f"🏖 Каоруко еще отдыхает. Приходи через {rem} ч.")

    outcome = random.choice(["win", "fail"])
    user_data[uid]["last_date"] = now
    
    if outcome == "win":
        user_data[uid]["exp"] += 15
        gif = "https://media.otakutalk.com/wp-content/uploads/2023/04/The-Fragrant-Flower-Blooms-With-Dignity-anime.gif" # Пляжная гифка (пример)
        await m.answer_animation(gif, caption="☀️ <b>Успех!</b>\nСвидание на пляже прошло идеально. Каоруко счастлива!\n<b>+15 EXP</b>", parse_mode="HTML")
    else:
        user_data[uid]["exp"] -= 5
        await m.answer("🌧 <b>Провал...</b>\nПошел дождь, и вы поссорились. Каоруко ушла домой одна.\n<b>-5 EXP</b>")

@dp.message(F.text.casefold() == "ты выйдешь за меня?")
async def marry_phrase(m: types.Message):
    if not m.reply_to_message: return
    uid, tid = m.from_user.id, m.reply_to_message.from_user.id
    check_user(uid, m.from_user.first_name)
    check_user(tid, m.reply_to_message.from_user.first_name)
    
    user_data[tid]["m_req"] = uid
    await m.answer(f"💍 {m.reply_to_message.from_user.mention_html()}, тут серьезный вопрос...\nНапиши <b>'согласен'</b> или <b>'отказ'</b>", parse_mode="HTML")

@dp.message()
async def global_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)

    if txt == "согласен" and user_data[uid].get("m_req"):
        rid = user_data[uid]["m_req"]
        user_data[uid]["partner"], user_data[rid]["partner"] = rid, uid
        user_data[uid]["m_req"] = None
        return await m.answer("💖 Теперь вы официально пара!")

    if txt in rp_actions and m.reply_to_message:
        act = rp_actions[txt]
        target = m.reply_to_message.from_user.mention_html()
        user_data[uid]["exp"] += 2
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.waifu.pics/sfw/{act['g']}") as r:
                url = (await r.json())["url"] if r.status == 200 else None
                msg = f"{m.from_user.mention_html()} {act['t'].format(target=target)}"
                if url: await m.answer_animation(url, caption=msg, parse_mode="HTML")
                else: await m.answer(msg, parse_mode="HTML")

async def main():
    keep_alive()
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())