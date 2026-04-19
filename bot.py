import asyncio, random, aiohttp, time, os, json, logging
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import BotCommand, ChatPermissions, ReplyParameters, ErrorEvent

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 
DB_FILE = "waguruko_god_db.json"

logging.basicConfig(level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Waguruko God Engine: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- МАССИВНАЯ СИСТЕМА ДАННЫХ ---
class Database:
    def __init__(self, path):
        self.path = path
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"users": {}, "admins": [OWNER_ID]}

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_u(self, uid, name=None):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {"name": name or f"Юзер_{uid}", "softness": 0, "last_cake": 0, "warns": 0}
        elif name:
            self.data["users"][uid]["name"] = name
        return self.data["users"][uid]

db = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СПИСОК РП ДЕЙСТВИЙ ---
RP_MAP = {
    "обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "гладить": "pat", 
    "уебать": "slap", "тык": "poke", "лизнуть": "lick", "прижаться": "cuddle",
    "потискать": "handhold", "смутиться": "blush", "обидеться": "cry", 
    "ударить": "punch", "похвалить": "highfive", "танцевать": "dance"
}

# --- БЛОК 1: ОБРАБОТЧИК КОМАНД (ЧЕРЕЗ СЛЕШ /) ---

@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):
    u = db.get_u(m.from_user.id, m.from_user.full_name)
    now = time.time()
    if now - u["last_cake"] < 3600:
        rem = int((3600 - (now - u["last_cake"])) / 60)
        return await m.reply(f"⏳ Твои щечки еще не готовы к новому тортику! Приходи через {rem} мин.")
    
    growth = random.randint(5, 25)
    u["softness"] += growth
    u["last_cake"] = now
    db.save()
    await m.reply(f"🍰 <b>Ням-ням!</b>\nЧерез команду ты скушал элитный торт.\nМягкость: <b>+{growth} ед.</b> (Итого: {u['softness']})", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    uid = m.from_user.id
    u = db.get_u(uid, m.from_user.full_name)
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in db.data["admins"] else "👤 Участник")
    res = (f"<b>『 🌸 Профиль Вагури 』</b>\n\n"
           f"👤 <b>Имя:</b> {u['name']}\n"
           f"🎖 <b>Статус:</b> {role}\n"
           f"☁️ <b>Мягкость щек:</b> {u['softness']} ед.\n"
           f"⚠️ <b>Варны:</b> {u['warns']}/3")
    await m.reply(res, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    top = sorted(db.data["users"].items(), key=lambda x: x[1]['softness'], reverse=True)[:10]
    res = "<b>☁️ Топ Самых Мягких Щечек чата:</b>\n\n"
    for i, (uid_s, d) in enumerate(top, 1):
        res += f"{i}. <a href='tg://user?id={uid_s}'>{d['name']}</a> — <b>{d['softness']}</b>\n"
    await m.answer(res, parse_mode="HTML")

@dp.message(Command("admins"))
async def cmd_admins(m: types.Message):
    res = "<b>👑 Любимчики Вагури (Админы):</b>\n\n"
    for i, adm_id in enumerate(db.data["admins"], 1):
        u_info = db.data["users"].get(str(adm_id))
        name = u_info["name"] if u_info else f"Друг ({adm_id})"
        res += f"{i}. <a href='tg://user?id={adm_id}'>{name}</a>\n"
    await m.answer(res, parse_mode="HTML")

# --- БЛОК 2: ТЕКСТОВЫЕ ТРИГГЕРЫ (БЕЗ СЛЕША) ---

@dp.message(F.text)
async def text_handler(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()
    u = db.get_u(uid, m.from_user.full_name)

    # Триггер на тортик словом
    if txt == "тортик":
        now = time.time()
        if now - u["last_cake"] < 3600:
            return await m.reply("⏳ Щечки еще сытые!")
        growth = random.randint(1, 20)
        u["softness"] += growth
        u["last_cake"] = now
        db.save()
        return await m.reply(f"🍰 Ты скушал тортик! Мягкость +{growth} ед.")

    # Модерация и РП (только если есть реплей)
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        t_u = db.get_u(target.id, target.full_name)

        # Модерка
        if uid in db.data["admins"] or uid == OWNER_ID:
            try:
                if txt == "+админ" and uid == OWNER_ID:
                    if target.id not in db.data["admins"]: db.data["admins"].append(target.id); db.save()
                    return await m.answer(f"💎 {target.first_name} теперь Админ!")
                
                if txt == "-админ" and uid == OWNER_ID:
                    if target.id in db.data["admins"]: db.data["admins"].remove(target.id); db.save()
                    return await m.answer(f"❌ {target.first_name} удален из админов.")

                if txt == "мут":
                    await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=15))
                    return await m.answer(f"🔇 {target.first_name} в муте на 15 мин.")

                if txt == "варн":
                    t_u["warns"] += 1
                    if t_u["warns"] >= 3:
                        await bot.ban_chat_member(m.chat.id, target.id)
                        t_u["warns"] = 0; db.save()
                        return await m.answer(f"👞 {target.first_name} забанен за 3 варна!")
                    db.save()
                    return await m.answer(f"⚠️ Варн {target.first_name}! [{t_u['warns']}/3]")

                if txt == "бан":
                    await bot.ban_chat_member(m.chat.id, target.id)
                    return await m.answer(f"👞 {target.first_name} изгнан!")
                
                if txt == "кик":
                    await bot.ban_chat_member(m.chat.id, target.id)
                    await bot.unban_chat_member(m.chat.id, target.id)
                    return await m.answer(f"👞 {target.first_name} кикнут!")
            except:
                return await m.reply("❌ Недостаточно прав!")

        # РП действия
        if txt in RP_MAP:
            async with aiohttp.ClientSession() as sess:
                try:
                    async with sess.get(f"https://api.waifu.pics/sfw/{RP_MAP[txt]}") as r:
                        data = await r.json()
                        await m.answer_animation(data["url"], caption=f"🌸 {m.from_user.mention_html()} {txt} {target.mention_html()}!", parse_mode="HTML")
                except:
                    await m.answer(f"🌸 {m.from_user.first_name} {txt} {target.first_name}!")

    # Очистка чата
    if txt.startswith("очистить") and (uid in db.data["admins"] or uid == OWNER_ID):
        try:
            num = int(txt.split()[1])
            num = min(num, 100)
            await m.delete()
            async for message in bot.get_chat_history(m.chat.id, limit=num):
                try: await message.delete()
                except: continue
        except: pass

# --- БЛОК 3: СИСТЕМНЫЕ ФУНКЦИИ ---

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="cake", description="Скушать тортик"),
        BotCommand(command="profile", description="Твой профиль"),
        BotCommand(command="top", description="Топ мягкости"),
        BotCommand(command="admins", description="Любимчики"),
    ]
    await bot.set_my_commands(commands)

@dp.message(F.new_chat_members)
async def welcome(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot: continue
        await m.answer(f"🌸 Добро пожаловать, {mem.mention_html()}! Я Вагури Каоруко. Напиши /cake чтобы начать расти!", parse_mode="HTML")

async def main():
    keep_alive()
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Глобальная ошибка: {e}")