import asyncio, random, aiohttp, time, os, json, logging
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions, ReplyParameters

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 
DB_FILE = "waguruko_ultimate_db.json"

logging.basicConfig(level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Waguruko God-Mode: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- СИСТЕМА БАЗЫ ДАННЫХ ---
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

# --- СЕКЦИЯ 1: КОМАНДЫ (ЧЕРЕЗ СЛЕШ /) ---

@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):
    u = db.get_u(m.from_user.id, m.from_user.full_name)
    now = time.time()
    if now - u["last_cake"] < 3600:
        rem = int((3600 - (now - u["last_cake"])) / 60)
        return await m.reply(f"⏳ Твои щечки еще не готовы! Жди {rem} мин.")
    growth = random.randint(5, 25)
    u["softness"] += growth
    u["last_cake"] = now
    db.save()
    await m.reply(f"🍰 <b>Мягкость щечек выросла!</b>\nРезультат: <b>+{growth} ед.</b> (Всего: {u['softness']})", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    uid = m.from_user.id
    u = db.get_u(uid, m.from_user.full_name)
    role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in db.data["admins"] else "👤 Участник")
    res = (f"<b>『 🌸 Профиль 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n🎖 <b>Статус:</b> {role}\n☁️ <b>Мягкость:</b> {u['softness']} ед.\n⚠️ <b>Варны:</b> {u['warns']}/3")
    await m.reply(res, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    top = sorted(db.data["users"].items(), key=lambda x: x[1]['softness'], reverse=True)[:10]
    res = "<b>☁️ Топ Самых Мягких Щечек:</b>\n\n"
    for i, (uid_s, d) in enumerate(top, 1):
        res += f"{i}. <a href='tg://user?id={uid_s}'>{d['name']}</a> — <b>{d['softness']}</b>\n"
    await m.answer(res, parse_mode="HTML")

# --- СЕКЦИЯ 2: ОБРАБОТЧИК ТЕКСТА (МОДЕРКА + РП) ---

@dp.message(F.text)
async def text_logic(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()
    u = db.get_u(uid, m.from_user.full_name)

    # Триггер на тортик без слеша
    if txt == "тортик":
        return await cmd_cake(m)

    # Разбан по ID (не реплей)
    if txt.startswith("разбан ") and (uid in db.data["admins"] or uid == OWNER_ID):
        try:
            t_id = int(txt.split()[1])
            await bot.unban_chat_member(m.chat.id, t_id, only_if_banned=True)
            return await m.answer(f"🔓 Пользователь {t_id} разбанен!")
        except: return await m.answer("❌ Формат: разбан [ID]")

    # Блок реплаев
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        t_u = db.get_u(target.id, target.full_name)

        # МОДЕРАЦИЯ
        if uid in db.data["admins"] or uid == OWNER_ID:
            try:
                if txt == "размут":
                    await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
                    return await m.answer(f"🔊 {target.first_name} размучен!")

                if txt == "разбан":
                    await bot.unban_chat_member(m.chat.id, target.id, only_if_banned=True)
                    return await m.answer(f"🔓 {target.first_name} разбанен!")

                if txt == "мут":
                    await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=15))
                    return await m.answer(f"🔇 {target.first_name} замолчал на 15 мин.")

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

                if txt == "+админ" and uid == OWNER_ID:
                    if target.id not in db.data["admins"]: db.data["admins"].append(target.id); db.save()
                    return await m.answer(f"💎 {target.first_name} теперь Админ!")

            except Exception as e:
                return await m.reply(f"❌ Ошибка прав: {e}")

        # РП ДЕЙСТВИЯ
        if txt in RP_MAP:
            async with aiohttp.ClientSession() as sess:
                try:
                    async with sess.get(f"https://api.waifu.pics/sfw/{RP_MAP[txt]}") as r:
                        data = await r.json()
                        await m.answer_animation(data["url"], caption=f"🌸 {m.from_user.mention_html()} {txt} {target.mention_html()}!", parse_mode="HTML")
                except: await m.answer(f"🌸 {m.from_user.first_name} {txt} {target.first_name}!")

    # Очистка чата
    if txt.startswith("очистить ") and (uid in db.data["admins"] or uid == OWNER_ID):
        try:
            num = min(int(txt.split()[1]), 100)
            await m.delete()
            async for msg in bot.get_chat_history(m.chat.id, limit=num):
                try: await msg.delete()
                except: continue
        except: pass

# --- СЕКЦИЯ 3: СИСТЕМНЫЙ ЗАПУСК ---

async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="cake", description="Тортик"),
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="top", description="Топ мягкости"),
    ])

@dp.message(F.new_chat_members)
async def welcome_bot(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot: continue
        await m.answer(f"🌸 Привет, {mem.mention_html()}! Я Вагури. Попробуй /cake!", parse_mode="HTML")

async def main():
    keep_alive()
    # УБИВАЕМ КОНФЛИКТЫ: удаляем старые вебхуки и зависшие сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")