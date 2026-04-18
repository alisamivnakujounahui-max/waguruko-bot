import asyncio, random, aiohttp, time, os
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko OS: Admin & Fun Live!"
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
            "last_date": 0, "warns": 0
        }

# Расширенный список РП (23 команды!)
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
    "лик": "лижет щечку {target} 👅", "сон": "укрывает {target} теплым одеялом 💤",
    "танец": "танцует вальс с {target} 💃", "ням": "угощает {target} вкусняшкой 🍰",
    "чмок": "дарит чмок {target} 😊", "игра": "играет в приставку с {target} 🎮",
    "секс": "наказывает {target} 🔞", "щекотка": "щекочет {target} ✨",
    "массаж": "мнет плечики {target} 💆‍♂️", "ванна": "плещется в воде с {target} 🛁",
    "подарок": "вручает милую коробочку {target} 🎁",
    "гладить": "гладит по голове {target} 🥺", "злиться": "топает ножками на {target} 💢",
    "грустить": "плачет на плече у {target} 💧", "радоваться": "прыгает от счастья с {target} ✨",
    "хвалить": "говорит, какой(ая) {target} молодец ⭐",
    "обидеться": "надул(а) губки на {target} 😤", "подмигнуть": "игриво подмигивает {target} 😉",
    "испугаться": "прячется за спину {target} 🙀"
}

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="help", description="Все команды"),
        BotCommand(command="date", description="Свидание с Каоруко"),
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="warns", description="Мои предупреждения"),
        BotCommand(command="top", description="Топ активных")
    ]
    await bot.set_my_commands(commands)

# --- МОДЕРАЦИЯ (МИЛАЯ) ---

@dp.message(F.new_chat_members)
async def welcome(m: types.Message):
    for user in m.new_chat_members:
        await m.answer(f"🌸 Добро пожаловать, {user.first_name}! Каоруко приготовила для тебя чай и тортик. Не обижай никого!")

@dp.message(F.text.casefold().startswith("мут"))
async def mute_user(m: types.Message):
    member = await m.chat.get_member(m.from_user.id)
    if not member.is_chat_admin(): return await m.reply("Только админы могут ставить в угол! 😤")
    if not m.reply_to_message: return await m.reply("Кому ротик заклеим? (ответь на соо)")
    
    await m.chat.restrict(m.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=10))
    await m.answer(f"🤫 {m.reply_to_message.from_user.first_name} отправлен(а) в уголок тишины на 10 минут.")

@dp.message(F.text.casefold().startswith("варн"))
async def warn_user(m: types.Message):
    member = await m.chat.get_member(m.from_user.id)
    if not member.is_chat_admin(): return
    if not m.reply_to_message: return
    
    uid = m.reply_to_message.from_user.id
    check_user(uid, m.reply_to_message.from_user.first_name)
    user_data[uid]["warns"] += 1
    
    if user_data[uid]["warns"] >= 3:
        await m.chat.ban(uid)
        await m.answer(f"🚫 {m.reply_to_message.from_user.first_name} набрал(а) 3 варна и покидает нас. Каоруко расстроена...")
    else:
        await m.answer(f"⚠️ {m.reply_to_message.from_user.first_name}, веди себя прилично! Предупреждение {user_data[uid]['warns']}/3")

# --- СВИДАНИЯ И РП ---

@dp.message(Command("date"))
async def cmd_date(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    now = time.time()
    if now - user_data[uid]["last_date"] < 14400:
        return await m.reply("⏳ Каоруко еще не отдохнула от прошлого раза!")

    user_data[uid]["last_date"] = now
    if random.randint(1, 100) <= 60:
        user_data[uid]["exp"] += 15
        await m.answer_animation("https://i.waifu.pics/vN7E2E0.gif", caption="🍰 <b>Удача!</b> Каоруко в восторге от прогулки.\n<b>+15 EXP</b>", parse_mode="HTML")
    else:
        user_data[uid]["exp"] -= 5
        await m.answer("🌧 Ой... Кажется, вы не нашли общий язык. Попробуй позже.")

@dp.message()
async def global_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)

    # РП Логика
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
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())