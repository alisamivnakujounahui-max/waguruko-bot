import asyncio, random, aiohttp, time, os, json, logging
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions, ErrorEvent

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 
DB_FILE = "waguruko_pure_db.json"

logging.basicConfig(level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Waguruko Pure Engine: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- СИСТЕМА ПАМЯТИ ---
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

# --- РП ДАННЫЕ (ГИФКИ) ---
RP_MAP = {
    "обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "гладить": "pat", 
    "уебать": "slap", "тык": "poke", "лизнуть": "lick", "прижаться": "cuddle",
    "потискать": "handhold", "смутиться": "blush", "обидеться": "cry", 
    "ударить": "punch", "похвалить": "highfive", "танцевать": "dance"
}

# --- ВСПОМОГАТЕЛЬНОЕ ---
async def is_admin(uid):
    return uid in db.data["admins"] or uid == OWNER_ID

# --- ОСНОВНОЙ ОБРАБОТЧИК ---
@dp.message()
async def core_handler(m: types.Message):
    if not m.text or m.from_user.is_bot: return
    
    uid = m.from_user.id
    txt = m.text.lower().strip()
    u = db.get_u(uid, m.from_user.full_name)
    
    # 1. СИСТЕМА ТОРТИКА (Текст + Команда)
    if txt in ["тортик", "/cake", f"/cake@{bot.id}"]:
        now = time.time()
        if now - u["last_cake"] < 3600:
            rem = int((3600 - (now - u["last_cake"])) / 60)
            return await m.reply(f"⏳ Щечки еще не переварили тортик! Подожди {rem} мин.")
        
        growth = random.randint(1, 25)
        u["softness"] += growth
        u["last_cake"] = now
        db.save()
        return await m.reply(f"🍰 <b>Ням!</b>\nМягкость щечек: <b>+{growth} ед.</b>\nВсего: <b>{u['softness']} ед.</b> ✨", parse_mode="HTML")

    # 2. ПРОФИЛЬ И ТОП
    if txt in ["профиль", "/profile"]:
        role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in db.data["admins"] else "👤 Участник")
        return await m.reply(f"<b>『 🌸 Профиль Вагури 』</b>\n\n👤 <b>Имя:</b> {u['name']}\n🎖 <b>Роль:</b> {role}\n☁️ <b>Мягкость:</b> {u['softness']} ед.\n⚠️ <b>Варны:</b> {u['warns']}/3", parse_mode="HTML")

    if txt in ["топ", "/top"]:
        top = sorted(db.data["users"].items(), key=lambda x: x[1]['softness'], reverse=True)[:10]
        res = "<b>☁️ Топ Самых Мягких Щечек:</b>\n\n"
        for i, (id_s, d) in enumerate(top, 1):
            res += f"{i}. <a href='tg://user?id={id_s}'>{d['name']}</a> — <b>{d['softness']}</b>\n"
        return await m.answer(res, parse_mode="HTML")

    # 3. БЛОК РЕПЛАЕВ (МОДЕРКА + РП)
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        t_u = db.get_u(target.id, target.full_name)
        
        # --- МОДЕРАЦИЯ ---
        if await is_admin(uid):
            try:
                if txt == "+админ" and uid == OWNER_ID:
                    if target.id not in db.data["admins"]: db.data["admins"].append(target.id); db.save()
                    return await m.answer(f"💎 <b>{target.first_name}</b> теперь Любимчик!")
                
                if txt == "-админ" and uid == OWNER_ID:
                    if target.id in db.data["admins"]: db.data["admins"].remove(target.id); db.save()
                    return await m.answer(f"❌ <b>{target.first_name}</b> убран из списка.")

                if txt == "мут":
                    await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=30))
                    return await m.answer(f"🔇 {target.first_name} замолчал на 30 минут.")

                if txt == "размут":
                    await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
                    return await m.answer(f"🔊 {target.first_name} размучен.")

                if txt == "варн":
                    t_u["warns"] += 1
                    if t_u["warns"] >= 3:
                        await bot.ban_chat_member(m.chat.id, target.id)
                        t_u["warns"] = 0; db.save()
                        return await m.answer(f"👞 {target.first_name} получил 3-й варн и был изгнан!")
                    db.save()
                    return await m.answer(f"⚠️ {target.first_name} предупрежден! [{t_u['warns']}/3]")

                if txt == "бан":
                    await bot.ban_chat_member(m.chat.id, target.id)
                    return await m.answer(f"👞 {target.first_name} изгнан!")

                if txt == "кик":
                    await bot.ban_chat_member(m.chat.id, target.id)
                    await bot.unban_chat_member(m.chat.id, target.id)
                    return await m.answer(f"👞 {target.first_name} вылетел из чата.")
            except Exception as e:
                return await m.reply(f"❌ Ошибка прав: скорее всего, у меня нет прав админа или цель выше меня по рангу.")

        # --- РП ДЕЙСТВИЯ ---
        if txt in RP_MAP:
            async with aiohttp.ClientSession() as sess:
                try:
                    async with sess.get(f"https://api.waifu.pics/sfw/{RP_MAP[txt]}") as r:
                        if r.status == 200:
                            data = await r.json()
                            await m.answer_animation(data["url"], caption=f"🌸 {m.from_user.mention_html()} <b>{txt}</b> {target.mention_html()}!", parse_mode="HTML")
                        else: raise Exception
                except:
                    await m.answer(f"🌸 {m.from_user.first_name} {txt} {target.first_name}!")

    # 4. ОЧИСТКА ЧАТА (Команда: очистить [число])
    if txt.startswith("очистить") and await is_admin(uid):
        try:
            parts = txt.split()
            num = int(parts[1]) if len(parts) > 1 else 10
            num = min(num, 100)
            await m.delete()
            deleted = 0
            async for message in bot.get_chat_history(m.chat.id, limit=num):
                try:
                    await message.delete()
                    deleted += 1
                except: continue
            status = await m.answer(f"🧹 Удалено сообщений: {deleted}")
            await asyncio.sleep(2); await status.delete()
        except: pass

# --- ИНИЦИАЛИЗАЦИЯ ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="cake", description="Скушать тортик"),
        BotCommand(command="profile", description="Профиль и мягкость"),
        BotCommand(command="top", description="Топ мягких щечек"),
        BotCommand(command="admins", description="Список админов"),
    ]
    await bot.set_my_commands(commands)

async def main():
    keep_alive()
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())