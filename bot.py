import asyncio
import random
import aiohttp
from aiogram import Bot, Dispatcher, types

TOKEN = "8678898798:AAHoQPa86QC04xkvc47kHxdluTQDj3LRhRI"

bot = Bot(token=TOKEN)
dp = Dispatcher()

rp_actions = {
    "обнять": {
        "texts": [
            "обнял(а) {target} 🤗",
            "крепко обнял(а) {target}"
        ],
        "gif": "hug"
    },
    "поцеловать": {
        "texts": [
            "поцеловал(а) {target} 💋"
        ],
        "gif": "kiss"
    },
    "ударить": {
        "texts": [
            "ударил(а) {target} 💥"
        ],
        "gif": "slap"
    },
    "погладить": {
        "texts": [
            "погладил(а) {target} 🥺"
        ],
        "gif": "pat"
    }
}


async def get_gif(action):
    url = f"https://api.waifu.pics/sfw/{action}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data["url"]


@dp.message()
async def rp_handler(message: types.Message):
    if not message.reply_to_message:
        return

    if not message.text:
        return

    action = message.text.lower().strip()

    if action in rp_actions:
        user = message.from_user.mention_html()
        target = message.reply_to_message.from_user.mention_html()

        text = random.choice(rp_actions[action]["texts"])
        gif_type = rp_actions[action]["gif"]

        gif_url = await get_gif(gif_type)

        await message.answer_animation(
            gif_url,
            caption=f"{user} {text.format(target=target)}",
            parse_mode="HTML"
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())