import asyncio, random, aiohttp, time, os, json, logging
from threading import Thread
from datetime import timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand, ChatPermissions

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635 
DB_FILE = "waguruko_final_db.json"

logging.basicConfig(level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Waguruko Command Engine: Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- ВЕЧНАЯ ПАМЯТЬ ---
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

    def get_user(self, uid, name=None):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {"name": name or f"Юзер_{uid}", "exp": 0, "softness": 0, "last_cake": 0}
        elif name:
            self.data["users"][uid]["name"] = name
        self.save()
        return self.data["users"][uid]

db = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ТОРТИКА ---
async def eat_cake_logic(m: types.Message):
    u = db.get_user(m.from_user.id, m.from_user.first_name)
    now = time.time()
    if now - u["last_cake"] < 3600:
        return await m.reply("⏳ Твои щечки еще не проголодались! Подожди часик.")
    
    growth = random.randint(0, 20)
    u["softness"] += growth
    u["last_cake"] = now
    db.save()
    await m.reply(f"🍰 <b>Ням!</b>\nМягкость твоих щечек выросла на <b>{growth} ед.</b>\nТеперь уровень нежности: <b>{u['softness']} ед.</b> ✨", parse_mode="HTML")

# --- РП И МОДЕРАЦИЯ (ОБРАБОТЧИК ТЕКСТА И КОМАНД) ---
RP_MAP = {"обнять": "hug", "поцеловать": "kiss", "кусь": "bite", "гладить": "pat", "уебать": "slap", "тык": "poke"}

@dp.message()
async def global_handler(m: types.Message):
    if not m.text: return
    txt = m.text.lower().strip()
    uid = m.from_user.id
    
    # Регистрация в базе
    db.get_user(uid, m.from_user.first_name)

    # 1. ТРИГГЕРЫ НА ТОРТИК
    if txt in ["тортик", "/cake", f"/cake@{bot.id}"]:
        return await eat_cake_logic(m)

    # 2. ПРОФИЛЬ И ТОП
    if txt in ["профиль", "/profile"]:
        u = db.get_user(uid)
        role = "👑 Создатель" if uid == OWNER_ID else ("🛡 Админ" if uid in db.data["admins"] else "👤 Участник")
        return await m.reply(f"<b>『 🌸 Профиль 』</b>\n\n👤 Имя: {u['name']}\n🎖 Роль: {role}\n💠 EXP: {u['exp']}\n☁️ Мягкость: {u['softness']} ед.", parse_mode="HTML")

    if txt in ["топ", "/top"]:
        top = sorted(db.data["users"].items(), key=lambda x: x[1]['softness'], reverse=True)[:10]
        res = "<b>☁️ Топ Мягких Щечек:</b>\n\n"
        for i, (id_str, data) in enumerate(top, 1):
            res += f"{i}. <a href='tg://user?id={id_str}'>{data['name']}</a> — {data['softness']} ед.\n"
        return await m.answer(res, parse_mode="HTML")

    if txt in ["админы", "любимчики", "/admins"]:
        res = "<b>👑 Любимчики Вагури:</b>\n\n"
        for i, adm_id in enumerate(db.data["admins"], 1):
            u_info = db.data["users"].get(str(adm_id))
            name = u_info["name"] if u_info else f"Друг ({adm_id})"
            res += f"{i}. <a href='tg://user?id={adm_id}'>{name}</a>\n"
        return await m.answer(res, parse_mode="HTML")

    # 3. ВЗАИМОДЕЙСТВИЯ (РЕПЛАИ)
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        db.get_user(target.id, target.first_name)

        # Модерация
        if uid in db.data["admins"]:
            if txt == "+админ" and uid == OWNER_ID:
                if target.id not in db.data["admins"]: db.data["admins"].append(target.id); db.save()
                return await m.answer(f"💎 {target.first_name} теперь в списке любимчиков!")
            if txt == "-админ" and uid == OWNER_ID:
                if target.id in db.data["admins"]: db.data["admins"].remove(target.id); db.save()
                return await m.answer(f"❌ {target.first_name} удален из списка.")
            if txt == "мут":
                await m.chat.restrict(target.id, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(minutes=15))
                return await m.answer(f"🔇 {target.first_name} замолчал на 15 мин.")
            if txt == "бан":
                await m.chat.ban(target.id)
                return await m.answer(f"👞 {target.first_name} изгнан навсегда.")

        # РП Команды
        if txt in RP_MAP:
            async with aiohttp.ClientSession() as sess:
                try:
                    async with sess.get(f"https://api.waifu.pics/sfw/{RP_MAP[txt]}") as r:
                        data = await r.json()
                        await m.answer_animation(data["url"], caption=f"🌸 {m.from_user.mention_html()} {txt} {target.mention_html()}!", parse_mode="HTML")
                        db.get_user(uid)["exp"] += 5; db.save()
                except:
                    await m.answer(f"🌸 {m.from_user.first_name} {txt} {target.first_name}!")

# --- ПРИВЕТСТВИЕ ---
@dp.message(F.new_chat_members)
async def welcome(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot: continue
        await m.answer(f"🌸 Приветик, {mem.mention_html()}! Я Вагури. Чтобы узнать мои команды, набери /help или просто нажми на <b>\</b>", parse_mode="HTML")

# --- РЕГИСТРАЦИЯ КОМАНД В ТГ ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="cake", description="Скушать тортик и вырастить щечки"),
        BotCommand(command="profile", description="Твой профиль и мягкость"),
        BotCommand(command="top", description="Топ самых мягких"),
        BotCommand(command="admins", description="Список любимчиков"),
        BotCommand(command="help", description="Список РП и команд"),
    ]
    await bot.set_my_commands(commands)

async def main():
    keep_alive()
    await set_commands(bot) # Магия: команды появятся в списке
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())