import asyncio, random, aiohttp, time, os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- ЗАГЛУШКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот запущен!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {} 
# Кулдаун для теста — 10 секунд, потом поменяешь на 3600 (час) или больше
CARD_COOLDOWN = 10 

# РП команды теперь работают и текстом (обнять), и через слэш (/hug)
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

# Ссылки заменены на более стабильные
characters = {
    "legendary": [
        {"name": "Вагури Каоруко", "rarity": "👑 ЛЕГЕНДАРКА (5%)", 
         "links": ["https://i.ibb.co/v4m0fXG/kaoruko.jpg"]}
    ],
    "common": [
        {"name": "Ринтаро Цумуги", "rarity": "⭐ Эпик", "links": ["https://i.ibb.co/fNfXWjK/rintaro.jpg"]},
        {"name": "Субару Хосина", "rarity": "💎 Редкое", "links": ["https://i.ibb.co/brq4h8m/subaru.jpg"]}
    ]
}

async def get_waifu_gif(action):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.waifu.pics/sfw/{action}") as r:
                if r.status == 200:
                    data = await r.json()
                    return data["url"]
    except: return None

def check_user(uid):
    if uid not in user_data: user_data[uid] = {"exp": 0, "last_card": 0}

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("🌸 Бот Waguruko готов к работе!\nНапиши /help, чтобы вспомнить всё.")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    text = (
        "<b>📂 Список команд:</b>\n\n"
        "🃏 <code>карточка</code> — выбить персонажа\n"
        "👤 /profile — твой опыт и ранг\n"
        "👋 /start — перезапуск\n\n"
        "<b>🎭 РП команды (в ответ на сообщение):</b>\n"
        "<i>обнять, поцеловать, кусь, ударить, вьебать, смутиться, трахнуть</i>"
    )
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    check_user(m.from_user.id)
    u = user_data[m.from_user.id]
    await m.answer(f"👤 <b>Профиль:</b> {m.from_user.first_name}\n💠 <b>Опыт:</b> {u['exp']}\n🏆 <b>Ранг:</b> Новичок", parse_mode="HTML")

@dp.message(F.text.casefold() == "карточка")
async def get_card(m: types.Message):
    uid = m.from_user.id
    check_user(uid)
    now = time.time()
    
    if now - user_data[uid]["last_card"] < CARD_COOLDOWN:
        rem = int(CARD_COOLDOWN - (now - user_data[uid]["last_card"]))
        return await m.reply(f"⏳ КД! Жди {rem} сек.")

    # Гача-логика
    pool = "legendary" if random.randint(1, 100) <= 5 else "common"
    char = random.choice(characters[pool])
    
    try:
        await m.answer_photo(random.choice(char["links"]), 
                           caption=f"🎁 <b>{char['name']}</b>\n✨ {char['rarity']}", 
                           parse_mode="HTML")
    except:
        await m.answer(f"✅ Выпал(а): {char['name']} ({char['rarity']})\n(Ошибка фото, но карта засчитана!)")
    
    user_data[uid]["last_card"] = now
    user_data[uid]["exp"] += 10

@dp.message()
async def rp_handler(m: types.Message):
    if not m.text or not m.reply_to_message: return
    act = m.text.lower().strip()
    if act in rp_actions:
        gif = await get_waifu_gif(rp_actions[act]["gif"])
        txt = f"{m.from_user.mention_html()} {rp_actions[act]['text'].format(target=m.reply_to_message.from_user.mention_html())}"
        check_user(m.from_user.id)
        user_data[m.from_user.id]["exp"] += 1
        if gif: await m.answer_animation(gif, caption=txt, parse_mode="HTML")
        else: await m.answer(txt, parse_mode="HTML")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())