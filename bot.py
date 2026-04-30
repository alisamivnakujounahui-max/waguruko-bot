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

BACKUP_CHANNEL = -1003866458811

DB_FILE = "waguruko_ultimate_db.json"

logging.basicConfig(level=logging.INFO)

# --- FLASK KEEP ALIVE ---

app = Flask('')

@app.route('/')
def home():
    return "Waguruko God-Mode: Online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- БАЗА ДАННЫХ ---

class Database:

    def __init__(self, path):
        self.path = path
        self.data = self.load_local()

    def load_local(self):

        if os.path.exists(self.path):

            try:

                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)

            except:
                pass

        return {
            "users": {},
            "admins": [OWNER_ID]
        }

    async def load_backup(self, bot):

        try:

            msgs = []

            async for msg in bot.get_chat_history(BACKUP_CHANNEL, limit=20):

                if msg.document:

                    if msg.document.file_name == self.path:
                        msgs.append(msg)

            if not msgs:
                print("BACKUP NOT FOUND")
                return

            latest = msgs[0]

            file = await bot.get_file(latest.document.file_id)

            await bot.download_file(file.file_path, self.path)

            with open(self.path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            print("DATABASE RESTORED FROM TELEGRAM")

        except Exception as e:

            print(f"BACKUP LOAD ERROR: {e}")

    async def backup(self, bot):

        try:

            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)

            await bot.send_document(
                BACKUP_CHANNEL,
                types.FSInputFile(self.path),
                caption="waguruko backup"
            )

            print("DATABASE BACKUP SAVED")

        except Exception as e:

            print(f"BACKUP SAVE ERROR: {e}")

    def save_local(self):

        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_u(self, uid, name=None):

        uid = str(uid)

        if uid not in self.data["users"]:

            self.data["users"][uid] = {
                "name": name or f"Юзер_{uid}",
                "softness": 0,
                "last_cake": 0,
                "warns": 0
            }

        elif name:

            self.data["users"][uid]["name"] = name

        return self.data["users"][uid]

# --- ИНИЦИАЛИЗАЦИЯ ---

db = Database(DB_FILE)

bot = Bot(token=TOKEN)

dp = Dispatcher()

# --- RP ДЕЙСТВИЯ ---

RP_MAP = {
    "обнять": "hug",
    "поцеловать": "kiss",
    "кусь": "bite",
    "гладить": "pat",
    "уебать": "slap",
    "тык": "poke",
    "лизнуть": "lick",
    "прижаться": "cuddle",
    "потискать": "handhold",
    "смутиться": "blush",
    "обидеться": "cry",
    "ударить": "punch",
    "похвалить": "highfive",
    "танцевать": "dance"
}

# --- /cake ---

@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):

    uid = m.from_user.id

    u = db.get_u(uid, m.from_user.full_name)

    now = time.time()

    if now - u["last_cake"] < 3600:

        rem = int((3600 - (now - u["last_cake"])) / 60)

        return await m.reply(
            f"⏳ Твои щечки еще не готовы! Жди {rem} мин."
        )

    if uid == OWNER_ID:

        growth = random.randint(50, 120)

    else:

        growth = random.randint(5, 25)

    u["softness"] += growth

    u["last_cake"] = now

    db.save_local()

    await db.backup(bot)

    await m.reply(
        f"🍰 <b>Мягкость щечек выросла!</b>\n"
        f"Результат: <b>+{growth} ед.</b> "
        f"(Всего: {u['softness']})",
        parse_mode="HTML"
    )

# --- /give ---

@dp.message(Command("give"))
async def cmd_give(m: types.Message):

    # 🔒 ТОЛЬКО ВЛАДЕЛЕЦ
    if m.from_user.id != OWNER_ID:
        return  # молча игнор

    if not m.reply_to_message:
        return await m.reply("❌ Ответь на сообщение пользователя")

    try:
        amount = int(m.text.split()[1])
    except:
        return await m.reply("❌ Формат: /give 100")

    target = m.reply_to_message.from_user
    u = db.get_u(target.id, target.full_name)

    u["softness"] += amount

    db.save_local()
    await db.backup(bot)

    await m.reply(
        f"🌸 Вагурочка подарила {target.mention_html()} "
        f"<b>+{amount}</b> мягкости!\n"
        f"☁️ Теперь у него: <b>{u['softness']}</b>",
        parse_mode="HTML"
    )

# --- /profile ---

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):

    uid = m.from_user.id

    u = db.get_u(uid, m.from_user.full_name)

    role = (
        "👑 Создатель"
        if uid == OWNER_ID
        else (
            "🛡 Админ"
            if uid in db.data["admins"]
            else "👤 Участник"
        )
    )

    res = (
        f"<b>『 🌸 Профиль 』</b>\n\n"
        f"👤 <b>Имя:</b> {u['name']}\n"
        f"🎖 <b>Статус:</b> {role}\n"
        f"☁️ <b>Мягкость:</b> {u['softness']} ед.\n"
        f"⚠️ <b>Варны:</b> {u['warns']}/3"
    )

    await m.reply(res, parse_mode="HTML")

# --- /top ---

@dp.message(Command("top"))
async def cmd_top(m: types.Message):

    top = sorted(
        db.data["users"].items(),
        key=lambda x: x[1]['softness'],
        reverse=True
    )[:10]

    res = "<b>☁️ Топ Самых Мягких Щечек:</b>\n\n"

    for i, (uid_s, d) in enumerate(top, 1):

        res += f"{i}. {d['name']} — <b>{d['softness']}</b>\n"

    await m.answer(res, parse_mode="HTML")

# --- /rp ---

@dp.message(Command("rp"))
async def cmd_rp(m: types.Message):

    res = "<b>🌸 RP команды:</b>\n\n"

    for k in RP_MAP.keys():

        res += f"• {k}\n"

    res += "\nОтветь на сообщение и напиши действие 💬"

    await m.answer(res, parse_mode="HTML")

# --- ТЕКСТОВАЯ ЛОГИКА ---

@dp.message(F.text)
async def text_logic(m: types.Message):

    uid = m.from_user.id

    txt = m.text.lower().strip()

    u = db.get_u(uid, m.from_user.full_name)

    if txt == "тортик":

        return await cmd_cake(m)

    if txt.startswith("разбан ") and (
        uid in db.data["admins"]
        or uid == OWNER_ID
    ):

        try:

            t_id = int(txt.split()[1])

            await bot.unban_chat_member(
                m.chat.id,
                t_id,
                only_if_banned=True
            )

            return await m.answer(
                f"🔓 Пользователь {t_id} разбанен!"
            )

        except:

            return await m.answer(
                "❌ Формат: разбан [ID]"
            )

    if m.reply_to_message:

        target = m.reply_to_message.from_user

        t_u = db.get_u(
            target.id,
            target.full_name
        )

        if uid in db.data["admins"] or uid == OWNER_ID:

            try:

                if txt == "размут":

                    await bot.restrict_chat_member(
                        m.chat.id,
                        target.id,
                        ChatPermissions(
                            can_send_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )

                    return await m.answer(
                        f"🔊 {target.first_name} размучен!"
                    )

                if txt == "разбан":

                    await bot.unban_chat_member(
                        m.chat.id,
                        target.id,
                        only_if_banned=True
                    )

                    return await m.answer(
                        f"🔓 {target.first_name} разбанен!"
                    )

                if txt == "мут":

                    await bot.restrict_chat_member(
                        m.chat.id,
                        target.id,
                        ChatPermissions(
                            can_send_messages=False
                        ),
                        until_date=timedelta(minutes=15)
                    )

                    return await m.answer(
                        f"🔇 {target.first_name} "
                        f"замолчал на 15 мин."
                    )

                if txt == "варн":

                    t_u["warns"] += 1

                    if t_u["warns"] >= 3:

                        await bot.ban_chat_member(
                            m.chat.id,
                            target.id
                        )

                        t_u["warns"] = 0

                        db.save_local()

                        await db.backup(bot)

                        return await m.answer(
                            f"👞 {target.first_name} "
                            f"забанен за 3 варна!"
                        )

                    db.save_local()

                    await db.backup(bot)

                    return await m.answer(
                        f"⚠️ Варн {target.first_name}! "
                        f"[{t_u['warns']}/3]"
                    )

                if txt == "бан":

                    await bot.ban_chat_member(
                        m.chat.id,
                        target.id
                    )

                    return await m.answer(
                        f"👞 {target.first_name} изгнан!"
                    )

                if txt == "кик":

                    await bot.ban_chat_member(
                        m.chat.id,
                        target.id
                    )

                    await bot.unban_chat_member(
                        m.chat.id,
                        target.id
                    )

                    return await m.answer(
                        f"👞 {target.first_name} кикнут!"
                    )

                if txt == "+админ" and uid == OWNER_ID:

                    if target.id not in db.data["admins"]:

                        db.data["admins"].append(target.id)

                        db.save_local()

                        await db.backup(bot)

                    return await m.answer(
                        f"💎 {target.first_name} теперь Админ!"
                    )

            except Exception as e:

                return await m.reply(
                    f"❌ Ошибка прав: {e}"
                )

        if txt in RP_MAP:

            async with aiohttp.ClientSession() as sess:

                try:

                    async with sess.get(
                        f"https://api.waifu.pics/sfw/{RP_MAP[txt]}"
                    ) as r:

                        data = await r.json()

                        await m.answer_animation(
                            data["url"],
                            caption=(
                                f"🌸 "
                                f"{m.from_user.mention_html()} "
                                f"{txt} "
                                f"{target.mention_html()}!"
                            ),
                            parse_mode="HTML"
                        )

                except:

                    await m.answer(
                        f"🌸 {m.from_user.first_name} "
                        f"{txt} "
                        f"{target.first_name}!"
                    )

    if txt.startswith("очистить ") and (
        uid in db.data["admins"]
        or uid == OWNER_ID
    ):

        try:

            num = min(int(txt.split()[1]), 100)

            await m.delete()

            async for msg in bot.get_chat_history(
                m.chat.id,
                limit=num
            ):

                try:

                    await msg.delete()

                except:
                    continue

        except:
            pass

# --- КОМАНДЫ БОТА ---

await bot.set_my_commands([
    BotCommand(command="cake", description="Тортик"),
    BotCommand(command="profile", description="Профиль"),
    BotCommand(command="top", description="Топ мягкости"),
    BotCommand(command="rp", description="Список RP команд"),
])

# --- ПРИВЕТСТВИЕ ---

@dp.message(F.new_chat_members)
async def welcome_bot(m: types.Message):

    for mem in m.new_chat_members:

        if mem.is_bot:
            continue

        await m.answer(
            f"🌸 Привет, "
            f"{mem.mention_html()}! "
            f"Я Вагури. Попробуй /cake!",
            parse_mode="HTML"
        )

# --- MAIN ---

async def main():

    keep_alive()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await db.load_backup(bot)

    await set_commands(bot)

    await dp.start_polling(
        bot,
        skip_updates=True
    )

# --- ЗАПУСК ---

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except Exception as e:

        print(f"CRITICAL ERROR: {e}")