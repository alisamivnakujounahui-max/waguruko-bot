import asyncio
import random
import aiohttp
import time
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных в памяти (сбросится при перезагрузке)
user_data = {} # {user_id: {"exp": 0, "last_card": 0}}

# РП действия
rp_actions = {
    "обнять": {"text": "обнял(а) {target} 🤗", "gif": "hug"},
    "поцеловать": {"text": "поцеловал(а) {target} 💋", "gif": "kiss"},
    "ударить": {"text": "ударил(а) {target} 💥", "gif": "slap"},
    "погладить": {"text": "погладил(а) {target} 🥺", "gif": "pat"},
    "кусь": {"text": "кусьнул(а) {target} за ушко 🦷", "gif": "bite"},
    "вьебать": {"text": "со всей дури вьебал(а) {target} 👊", "gif": "slap"},
    "смутиться": {"text": "покраснел(а) перед {target} 😳", "gif": "blush"},
    "разозлиться": {"text": "злится на {target} 💢", "gif": "bully"}
}

# База персонажей
characters = {
    "legendary": [
        {"name": "Вагури Каоруко", "rarity": "👑 ЛЕГЕНДАРКА (5%)", 
         "links": [
             "https://i.pinimg.com/736x/83/9a/9e/839a9e225f69595f5904d023f2f81640.jpg",
             "https://i.pinimg.com/736x/95/8e/9e/958e9e160e1814660858e9668d90479b.jpg",
             "https://i.pinimg.com/736x/21/6b/0d/216b0df3f090d8102a061c5e6221c60a.jpg",
             "https://i.pinimg.com/736x/ec/11/4f/ec114f447f525547926715f3ec561331.jpg",
             "https://i.pinimg.com/736x/60/a4/0c/60a40c66063683f278070857736657c6.jpg",
             "https://i.pinimg.com/736x/0a/61/4d/0a614d0233488730953a9486c8d76962.jpg",
             "https://i.pinimg.com/736x/8c/7a/83/8c7a8359286d91f24d9f67a6f958742d.jpg",
             "https://i.pinimg.com/736x/1d/15/8e/1d158e939f50f7572d4c098909890e18.jpg"
         ]}
    ],
    "common": [
        {"name": "Ринтаро Цумуги", "rarity": "⭐ Эпик", "links": ["https://i.pinimg.com/736x/60/7b/0a/607b0a39f655681198f828038676d999.jpg", "https://i.pinimg.com/736x/4d/9d/2c/4d9d2c608f6540989180905963841143.jpg"]},
        {"name": "Субару Хосина", "rarity": "💎 Редкое", "links": ["https://i.pinimg.com/736x/44/2c/8d/442c8d50b7305904f65306637494f653.jpg", "https://i.pinimg.com/736x/a1/b2/c3/a1b2c3d4e5f6g7h8i9j0.jpg"]},
        {"name": "Саку Сакума", "rarity": "💎 Редкое", "links": ["https://i.pinimg.com/736x/11/43/8d/11438d56b46180373809618090596384.jpg"]},
        {"name": "Усами Сёхэй", "rarity": "⚪ Обычное", "links": ["https://i.pinimg.com/736x/8d/41/52/8d415264386763412581635341251341.jpg"]}
    ]
}

async def get_waifu_gif(action):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.waifu.pics/sfw/{action}") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["url"]
    return None

def check_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"exp": 0, "last_card": 0}

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Я бот по аниме 'Завтра я стану чьей-то девушкой' (и не только). \n\nПиши /help, чтобы увидеть команды.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "<b>🎮 Игровые команды:</b>\n"
        "• <code>карточка</code> — выбить случайного персонажа (КД 1 мин)\n"
        "• /profile — твоя статистика\n\n"
        "<b>🎭 РП Команды (ответом на сообщение):</b>\n"
        "• обнять, поцеловать, ударить, погладить, кусь, вьебать, смутиться, разозлиться"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    check_user(message.from_user.id)
    exp = user_data[message.from_user.id]["exp"]
    await message.answer(f"👤 <b>Профиль {message.from_user.first_name}</b>\n\n💠 Опыт общения: {exp}\n🏆 Ранг: {'Новичок' if exp < 50 else 'Олд'}", parse_mode="HTML")

# --- ГАЧА ---

@dp.message(F.text.casefold() == "карточка")
async def get_card(message: types.Message):
    uid = message.from_user.id
    check_user(uid)
    
    now = time.time()
    if now - user_data[uid]["last_card"] < 60:
        rem = int(60 - (now - user_data[uid]["last_card"]))
        return await message.reply(f"⏳ Кулдаун! Подожди {rem} сек.")

    char = random.choice(characters["legendary"] if random.randint(1, 100) <= 5 else characters["common"])
    photo = random.choice(char["links"])
    
    try:
        await message.answer_photo(photo, caption=f"🎁 <b>{char['name']}</b>\n✨ {char['rarity']}", parse_mode="HTML")
        user_data[uid]["last_card"] = now
        user_data[uid]["exp"] += 10
    except:
        await message.answer(f"❌ Ошибка фото, но тебе выпал: {char['name']}")

# --- РП ОБРАБОТЧИК ---

@dp.message()
async def global_handler(message: types.Message):
    if not message.text: return
    
    act = message.text.lower().strip()
    if act in rp_actions and message.reply_to_message:
        gif = await get_waifu_gif(rp_actions[act]["gif"])
        user = message.from_user.mention_html()
        target = message.reply_to_message.from_user.mention_html()
        caption = f"{user} {rp_actions[act]['text'].format(target=target)}"
        
        check_user(message.from_user.id)
        user_data[message.from_user.id]["exp"] += 1

        if gif:
            await message.answer_animation(gif, caption=caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())