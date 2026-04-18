import asyncio
import random
import aiohttp
import time
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- НЕВИДИМЫЙ ЩИТ ОТ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "OK"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 

rp_actions = {
    "обнять": {"text": "обнял(а) {target} 🤗", "gif": "hug"},
    "поцеловать": {"text": "поцеловал(а) {target} 💋", "gif": "kiss"},
    "ударить": {"text": "ударил(а) {target} 💥", "gif": "slap"},
    "погладить": {"text": "погладил(а) {target} 🥺", "gif": "pat"},
    "кусь": {"text": "сделал(а) кусь {target} 🦷", "gif": "bite"},
    "вьебать": {"text": "вьебал(а) {target} с ноги 👊", "gif": "slap"},
    "смутиться": {"text": "покраснел(а) от слов {target} 😳", "gif": "blush"},
    "разозлиться": {"text": "злится на {target} 💢", "gif": "bully"},
    "трахнуть": {"text": "жестко отодрал(а) {target} 🔞", "gif": "spank"}
}

characters = {
    "legendary": [
        {"name": "Вагури Каоруко", "rarity": "👑 ЛЕГЕНДАРКА (5%)", 
         "links": [
             "https://i.postimg.cc/q73W8L7j/kaoruko1.jpg", 
             "https://i.postimg.cc/mD8xR3y0/kaoruko2.jpg"
         ]}
    ],
    "common": [
        {"name": "Ринтаро Цумуги", "rarity": "⭐ Эпик", "links": ["https://i.postimg.cc/9f0vY0zP/rintaro.jpg"]},
        {"name": "Субару Хосина", "rarity": "💎 Редкое", "links": ["https://i.postimg.cc/4NfXWjK6/subaru.jpg"]},
        {"name": "Саку Сакума", "rarity": "💎 Редкое", "links": ["https://i.postimg.cc/brq4h8mD/saku.jpg"]}
    ]
}

async def get_waifu_gif(action):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.waifu.pics/sfw/{action}", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["url"]
    except: return None
    return None

def check_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"exp": 0, "last_card": 0}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🌸 Привет! Я Waguruko Bot.\n\nКоманды:\n/help — список команд\nкарточка — выбить персонажа")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("🎮 <b>Игры:</b>\n• карточка (1 мин КД)\n• /profile\n\n🎭 <b>РП:</b>\nобнять, кусь, вьебать и др. (в ответ на соо)", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    check_user(message.from_user.id)
    exp = user_data[message.from_user.id]["exp"]
    await message.answer(f"👤 <b>Профиль:</b> {message.from_user.first_name}\n💠 Опыт: {exp}", parse_mode="HTML")

@dp.message(F.text.casefold() == "карточка")
async def get_card(message: types.Message):
    uid = message.from_user.id
    check_user(uid)
    now = time.time()
    if now - user_data[uid]["last_card"] < 60:
        return await message.reply(f"⏳ Подожди {int(60-(now-user_data[uid]['last_card']))} сек.")

    char = random.choice(characters["legendary"] if random.randint(1, 100) <= 5 else characters["common"])
    photo = random.choice(char["links"])
    
    try:
        await message.answer_photo(photo, caption=f"🎁 <b>{char['name']}</b>\n✨ {char['rarity']}", parse_mode="HTML")
        user_data[uid]["last_card"] = now
        user_data[uid]["exp"] += 10
    except Exception as e:
        await message.answer(f"✅ Выпал(а): {char['name']} ({char['rarity']})\n(Картинка не прогрузилась, но карта в коллекции!)")
        user_data[uid]["last_card"] = now

@dp.message()
async def global_handler(message: types.Message):
    if not message.text or not message.reply_to_message: return
    act = message.text.lower().strip()
    if act in rp_actions:
        gif = await get_waifu_gif(rp_actions[act]["gif"])
        caption = f"{message.from_user.mention_html()} {rp_actions[act]['text'].format(target=message.reply_to_message.from_user.mention_html())}"
        check_user(message.from_user.id)
        user_data[message.from_user.id]["exp"] += 1
        if gif: await message.answer_animation(gif, caption=caption, parse_mode="HTML")
        else: await message.answer(caption, parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # Победит ошибку порта
    asyncio.run(main())