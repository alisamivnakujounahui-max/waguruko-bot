import asyncio, random, aiohttp, time, os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- НЕВИДИМЫЙ ЩИТ ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот Каоруко активен!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 
COOLDOWN_TIME = 60 # 1 минута кулдауна

# РП действия
rp_actions = {
    "обнять": {"text": "обнял(а) {target} 🤗", "gif": "hug"},
    "поцеловать": {"text": "поцеловал(а) {target} 💋", "gif": "kiss"},
    "ударить": {"text": "ударил(а) {target} 💥", "gif": "slap"},
    "погладить": {"text": "погладил(а) {target} 🥺", "gif": "pat"},
    "кусь": {"text": "сделал(а) кусь {target} 🦷", "gif": "bite"},
    "вьебать": {"text": "вьебал(а) {target} с ноги 👊", "gif": "slap"},
    "смутиться": {"text": "покраснел(а) перед {target} 😳", "gif": "blush"},
    "трахнуть": {"text": "жестко отодрал(а) {target} 🔞", "gif": "spank"}
}

# База персонажей (новые ссылки)
characters = {
    "legendary": [
        {"name": "Вагури Каоруко", "rarity": "👑 ЛЕГЕНДАРКА (5%)", 
         "links": ["https://img2.joyreactor.cc/pics/post/full/Kaoruko-Waguri-The-Fragrant-Flower-Blooms-With-Dignity-Anime-7566162.jpeg"]}
    ],
    "common": [
        {"name": "Ринтаро Цумуги", "rarity": "⭐ Эпик", "links": ["https://pic.rutubelist.ru/user/3b/03/3b03882772671239c89423b497042898.jpg"]},
        {"name": "Субару Хосина", "rarity": "💎 Редкое", "links": ["https://i.pinimg.com/originals/44/2c/8d/442c8d50b7305904f65306637494f653.jpg"]},
        {"name": "Саку Сакума", "rarity": "💎 Редкое", "links": ["https://i.pinimg.com/originals/91/92/72/91927233633215569424321234567890.jpg"]}
    ]
}

async def get_waifu_gif(action):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.waifu.pics/sfw/{action}", timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["url"]
    except: return None

def check_user(uid):
    if uid not in user_data: user_data[uid] = {"exp": 0, "last_card": 0}

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer(f"🌸 Привет, {m.from_user.first_name}!\nЯ бот Каоруко. Напиши /help чтобы увидеть что я могу.")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    text = (
        "<b>🎮 Основное:</b>\n"
        "• <code>карточка</code> — выбить персонажа (КД 1 мин)\n"
        "• /profile — твой опыт\n\n"
        "<b>🎭 РП команды (ответом на сообщение):</b>\n"
        "<i>обнять, поцеловать, кусь, ударить, вьебать, смутиться, трахнуть</i>"
    )
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    check_user(m.from_user.id)
    u = user_data[m.from_user.id]
    await m.answer(f"👤 <b>Профиль:</b> {m.from_user.first_name}\n💠 <b>Опыт:</b> {u['exp']}", parse_mode="HTML")

@dp.message(F.text.casefold() == "карточка")
async def get_card(m: types.Message):
    uid = m.from_user.id
    check_user(uid)
    now = time.time()
    
    if now - user_data[uid]["last_card"] < COOLDOWN_TIME:
        rem = int(COOLDOWN_TIME - (now - user_data[uid]["last_card"]))
        return await m.reply(f"⏳ КД! Жди {rem} сек.")

    pool = "legendary" if random.randint(1, 100) <= 5 else "common"
    char = random.choice(characters[pool])
    photo = random.choice(char["links"])
    
    try:
        await m.answer_photo(photo, caption=f"🎁 <b>{char['name']}</b>\n✨ {char['rarity']}", parse_mode="HTML")
    except:
        await m.answer(f"✅ Выпал(а): <b>{char['name']}</b> ({char['rarity']})\n(Ошибка фото, но карта засчитана!)", parse_mode="HTML")
    
    user_data[uid]["last_card"] = now
    user_data[uid]["exp"] += 10

@dp.message()
async def rp_handler(m: types.Message):
    if not m.text or not m.reply_to_message: return
    act = m.text.lower().strip()
    if act in rp_actions:
        gif = await get_waifu_gif(rp_actions[act]["gif"])
        target = m.reply_to_message.from_user.mention_html()
        txt = f"{m.from_user.mention_html()} {rp_actions[act]['text'].format(target=target)}"
        check_user(m.from_user.id)
        user_data[m.from_user.id]["exp"] += 1
        if gif: await m.answer_animation(gif, caption=txt, parse_mode="HTML")
        else: await m.answer(txt, parse_mode="HTML")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())