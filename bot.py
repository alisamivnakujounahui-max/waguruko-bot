import asyncio
import random
import aiohttp
import time
import os
from aiogram import Bot, Dispatcher, types

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кулдауны (сбросятся при перезагрузке сервера)
user_cooldowns = {}

rp_actions = {
    "обнять": {"texts": ["обнял(а) {target} 🤗"], "gif": "hug"},
    "поцеловать": {"texts": ["поцеловал(а) {target} 💋"], "gif": "kiss"},
    "ударить": {"texts": ["ударил(а) {target} 💥"], "gif": "slap"},
    "погладить": {"texts": ["погладил(а) {target} 🥺"], "gif": "pat"},
    "кусь": {"texts": ["кусьнул(а) {target} 🦷"], "gif": "bite"},
    "вьебать": {"texts": ["со всей дури вьебал(а) {target} по лицу 👊"], "gif": "slap"}
}

characters_data = {
    "legendary": [
        {"name": "Вагури Каоруко", "rarity": "👑 ЛЕГЕНДАРКА (5%)", 
         "links": [
             "https://i.pinimg.com/736x/83/9a/9e/839a9e225f69595f5904d023f2f81640.jpg",
             "https://i.pinimg.com/736x/95/8e/9e/958e9e160e1814660858e9668d90479b.jpg",
             "https://i.pinimg.com/736x/21/6b/0d/216b0df3f090d8102a061c5e6221c60a.jpg",
             "https://i.pinimg.com/736x/ec/11/4f/ec114f447f525547926715f3ec561331.jpg"
         ]}
    ],
    "common": [
        {"name": "Ринтаро Цумуги", "rarity": "⭐ Эпик", 
         "links": ["https://i.pinimg.com/736x/60/7b/0a/607b0a39f655681198f828038676d999.jpg"]},
        {"name": "Субару Хосина", "rarity": "💎 Редкое", 
         "links": ["https://i.pinimg.com/736x/44/2c/8d/442c8d50b7305904f65306637494f653.jpg"]},
        {"name": "Саку Сакума", "rarity": "💎 Редкое", 
         "links": ["https://i.pinimg.com/736x/11/43/8d/11438d56b46180373809618090596384.jpg"]},
        {"name": "Усами Сёхэй", "rarity": "⚪ Обычное", 
         "links": ["https://i.pinimg.com/736x/8d/41/52/8d415264386763412581635341251341.jpg"]}
    ]
}

async def get_gif(action):
    url = f"https://api.waifu.pics/sfw/{action}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["url"]
    except:
        return None

@dp.message(lambda message: message.text and message.text.lower().strip() == "карточка")
async def get_card(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()
    COOLDOWN = 10800 # 3 часа

    if user_id in user_cooldowns and (current_time - user_cooldowns[user_id] < COOLDOWN):
        rem = int((COOLDOWN - (current_time - user_cooldowns[user_id])) / 60)
        await message.reply(f"⏳ Кулдаун! Еще {rem // 60}ч. {rem % 60}мин.")
        return

    chance = random.randint(1, 100)
    char = random.choice(characters_data["legendary"] if chance <= 5 else characters_data["common"])
    
    user_cooldowns[user_id] = current_time
    await message.answer_photo(
        random.choice(char["links"]),
        caption=f"🎁 <b>{char['name']}</b>\n✨ Редкость: {char['rarity']}\n👤 Игрок: {message.from_user.mention_html()}",
        parse_mode="HTML"
    )

@dp.message()
async def rp_handler(message: types.Message):
    if not message.text or not message.reply_to_message:
        return

    action = message.text.lower().strip()
    if action in rp_actions:
        user = message.from_user.mention_html()
        target = message.reply_to_message.from_user.mention_html()
        
        gif_url = await get_gif(rp_actions[action]["gif"])
        text = random.choice(rp_actions[action]["texts"]).format(target=target)

        if gif_url:
            await message.answer_animation(gif_url, caption=f"{user} {text}", parse_mode="HTML")
        else:
            await message.answer(f"{user} {text}", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())