import asyncio, random, aiohttp, time, os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- ЗАГЛУШКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Waguruko Engine 2.0 Active!"
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
            "name": name,
            "exp": 0, 
            "partner": None, 
            "m_req": None,
            "stats": {"hugs": 0, "bites": 0, "slaps": 0, "total_rp": 0}
        }

rp_actions = {
    "обнять": {"text": "обнял(а) {target} 🤗", "gif": "hug", "stat": "hugs"},
    "поцеловать": {"text": "поцеловал(а) {target} 💋", "gif": "kiss", "stat": "total_rp"},
    "кусь": {"text": "сделал(а) кусь {target} 🦷", "gif": "bite", "stat": "bites"},
    "вьебать": {"text": "вьебал(а) {target} с ноги 👊", "gif": "slap", "stat": "slaps"},
    "ударить": {"text": "ударил(а) {target} 💥", "gif": "slap", "stat": "slaps"},
    "смутиться": {"text": "покраснел(а) перед {target} 😳", "gif": "blush", "stat": "total_rp"},
    "трахнуть": {"text": "жестко отодрал(а) {target} 🔞", "gif": "spank", "stat": "total_rp"}
}

# --- КОМАНДЫ ---

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    await m.answer(
        "<b>🌸 Команды Waguruko:</b>\n\n"
        "💍 <b>Семья:</b>\n"
        "• /marry — предложить брак (реплаем)\n"
        "• /divorce — развод\n\n"
        "<b>👤 Аккаунт:</b>\n"
        "• /profile — твоя стата и доверие Каоруко\n"
        "• /top — топ активных игроков\n\n"
        "<b>🎭 РП (реплаем):</b>\n"
        "<i>обнять, кусь, вьебать, поцеловать, смутиться, трахнуть</i>",
        parse_mode="HTML"
    )

@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message: return await m.reply("Ответь на сообщение того, с кем хочешь создать семью!")
    uid, tid = m.from_user.id, m.reply_to_message.from_user.id
    if uid == tid: return await m.reply("Сам на себе? Каоруко расстроена таким выбором...")
    
    check_user(uid, m.from_user.first_name)
    check_user(tid, m.reply_to_message.from_user.first_name)
    
    if user_data[uid]['partner']: return await m.reply("Ты уже в браке! Сначала /divorce")
    
    user_data[tid]["m_req"] = uid
    await m.answer(f"💍 {m.reply_to_message.from_user.mention_html()}, ты согласен(а) вступить в брак с {m.from_user.mention_html()}?\nНапиши <b>'согласен'</b> или <b>'отказ'</b>", parse_mode="HTML")

@dp.message(Command("divorce"))
async def cmd_divorce(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    if not user_data[uid]['partner']: return await m.reply("Ты и так свободен как ветер.")
    
    pid = user_data[uid]['partner']
    user_data[uid]['partner'] = None
    if pid in user_data: user_data[pid]['partner'] = None
    await m.answer("💔 Семейные узы разорваны...")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)
    u = user_data[uid]
    
    partner_name = "Нет"
    if u['partner']:
        pid = u['partner']
        partner_name = user_data[pid]['name'] if pid in user_data else "Твой любимка"

    # Текст про доверие Каоруко
    trust = "Низкое ☁️"
    if u['exp'] > 100: trust = "Дружеское 🌸"
    if u['exp'] > 500: trust = "Крепкое ✨"
    if u['exp'] > 1000: trust = "Твой мейн! 👑"

    text = (
        f"👤 <b>Профиль:</b> {m.from_user.first_name}\n"
        f"💍 <b>Пара:</b> {partner_name}\n"
        f"📈 <b>Доверие Каоруко:</b> {trust}\n"
        f"💠 <b>Опыт:</b> {u['exp']}\n\n"
        f"<b>📊 Статистика РП:</b>\n"
        f"🫂 Обнимашек: {u['stats']['hugs']}\n"
        f"🦷 Кусей: {u['stats']['bites']}\n"
        f"👊 Вьебалов: {u['stats']['slaps']}"
    )
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['exp'], reverse=True)[:5]
    top_text = "<b>🏆 Топ любимчиков Каоруко:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        top_text += f"{i}. {data['name']} — {data['exp']} EXP\n"
    await m.answer(top_text, parse_mode="HTML")

# --- ОБРАБОТЧИК ---

@dp.message()
async def global_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    check_user(uid, m.from_user.first_name)

    # Принятие брака
    if txt == "согласен" and user_data[uid]["m_req"]:
        rid = user_data[uid]["m_req"]
        user_data[uid]["partner"] = rid
        user_data[rid]["partner"] = uid
        user_data[uid]["m_req"] = None
        return await m.answer(f"🎉 Поздравляем! {m.from_user.mention_html()} и {user_data[rid]['name']} теперь семья!", parse_mode="HTML")

    # РП команды
    if txt in rp_actions and m.reply_to_message:
        target = m.reply_to_message.from_user.mention_html()
        act = rp_actions[txt]
        
        # Обновляем статику
        user_data[uid]["stats"][act["stat"]] += 1
        user_data[uid]["exp"] += 5
        
        caption = f"{m.from_user.mention_html()} {act['text'].format(target=target)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.waifu.pics/sfw/{act['gif']}") as r:
                if r.status == 200:
                    data = await r.json()
                    await m.answer_animation(data["url"], caption=caption, parse_mode="HTML")
                else:
                    await m.answer(caption, parse_mode="HTML")

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())