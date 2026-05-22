import asyncio
import random
import aiohttp
import time
import os
import logging

from threading import Thread
from datetime import datetime, timedelta, timezone

import aiosqlite
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    ChatPermissions,
    FSInputFile
)

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN")

OWNER_ID = 7799004635

BACKUP_CHANNEL = -1003866458811

DB_FILE = "waguruko.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# =========================================================
# FLASK KEEP ALIVE
# =========================================================

app = Flask("")


@app.route("/")
def home():
    return "Waguruko God-Mode: Online"


def run_flask():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    Thread(target=run_flask, daemon=True).start()

# =========================================================
# DATABASE
# =========================================================


class Database:

    def __init__(self, path):
        self.path = path
        self.conn = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()
        await self.conn.commit()
        log.info("Database initialized")

    async def _create_tables(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid         INTEGER PRIMARY KEY,
                name        TEXT    NOT NULL DEFAULT 'Юзер',
                softness    INTEGER NOT NULL DEFAULT 0,
                last_cake   REAL    NOT NULL DEFAULT 0,
                warns       INTEGER NOT NULL DEFAULT 0,
                reg_date    REAL    NOT NULL DEFAULT 0
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                uid INTEGER PRIMARY KEY
            )
        """)
        await self.conn.execute(
            "INSERT OR IGNORE INTO admins (uid) VALUES (?)",
            (OWNER_ID,)
        )

    # ---------------------------
    # USERS
    # ---------------------------

    async def get_user(self, uid: int, name: str = None):
        async with self.conn.execute(
            "SELECT * FROM users WHERE uid = ?", (uid,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            now = time.time()
            await self.conn.execute(
                """INSERT INTO users
                   (uid, name, softness, last_cake, warns, reg_date)
                   VALUES (?, ?, 0, 0, 0, ?)""",
                (uid, name or f"Юзер_{uid}", now)
            )
            await self.conn.commit()
            return {
                "uid": uid,
                "name": name or f"Юзер_{uid}",
                "softness": 0,
                "last_cake": 0,
                "warns": 0,
                "reg_date": now
            }
        else:
            if name and row["name"] != name:
                await self.conn.execute(
                    "UPDATE users SET name = ? WHERE uid = ?",
                    (name, uid)
                )
                await self.conn.commit()
            return dict(row)

    async def update_softness(self, uid: int, delta: int):
        await self.conn.execute(
            "UPDATE users SET softness = MAX(0, softness + ?) WHERE uid = ?",
            (delta, uid)
        )
        await self.conn.commit()

    async def set_softness(self, uid: int, value: int):
        await self.conn.execute(
            "UPDATE users SET softness = ? WHERE uid = ?",
            (max(0, value), uid)
        )
        await self.conn.commit()

    async def update_last_cake(self, uid: int, ts: float):
        await self.conn.execute(
            "UPDATE users SET last_cake = ? WHERE uid = ?",
            (ts, uid)
        )
        await self.conn.commit()

    async def update_warns(self, uid: int, value: int):
        await self.conn.execute(
            "UPDATE users SET warns = ? WHERE uid = ?",
            (value, uid)
        )
        await self.conn.commit()

    async def get_top(self, limit: int = 10):
        async with self.conn.execute(
            "SELECT name, softness FROM users ORDER BY softness DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()

    # ---------------------------
    # ADMINS
    # ---------------------------

    async def is_admin(self, uid: int) -> bool:
        async with self.conn.execute(
            "SELECT 1 FROM admins WHERE uid = ?", (uid,)
        ) as cur:
            return await cur.fetchone() is not None

    async def add_admin(self, uid: int):
        await self.conn.execute(
            "INSERT OR IGNORE INTO admins (uid) VALUES (?)", (uid,)
        )
        await self.conn.commit()

    async def remove_admin(self, uid: int):
        await self.conn.execute(
            "DELETE FROM admins WHERE uid = ?", (uid,)
        )
        await self.conn.commit()

    # ---------------------------
    # BACKUP
    # ---------------------------

    async def backup(self, bot_instance):
        try:
            await self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            await bot_instance.send_document(
                BACKUP_CHANNEL,
                FSInputFile(self.path),
                caption=f"📦 waguruko backup | {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            log.info("Backup sent to Telegram")
        except Exception as e:
            log.error(f"Backup error: {e}")


# =========================================================
# INIT
# =========================================================

db = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# RP ACTIONS
# =========================================================

RP_MAP = {
    "обнять":     {"api": "hug",      "text": "нежно обнял(а)"},
    "поцеловать": {"api": "kiss",     "text": "поцеловал(а)"},
    "кусь":       {"api": "bite",     "text": "кусьнул(а)"},
    "гладить":    {"api": "pat",      "text": "погладил(а)"},
    "уебать":     {"api": "slap",     "text": "жестко уебал(а)"},
    "тык":        {"api": "poke",     "text": "тыкнул(а)"},
    "лизнуть":    {"api": "lick",     "text": "лизнул(а)"},
    "прижаться":  {"api": "cuddle",   "text": "прижался(ась) к"},
    "потискать":  {"api": "cuddle",   "text": "затискал(а)"},
    "танцевать":  {"api": "dance",    "text": "танцует с"},
    "держать":    {"api": "handhold", "text": "взял(а) за руку"},
    "спать":      {"api": "sleep",    "text": "уснул(а) рядом с"},
    "смущать":    {"api": "blush",    "text": "засмущал(а)"},
    "кормить":    {"api": "feed",     "text": "кормит"},
    "флирт":      {"api": "smile",    "text": "флиртует с"},
    "убить":      {"api": "kick",     "text": "уничтожил(а)"},
}

# =========================================================
# BOT COMMANDS
# =========================================================


async def set_commands(bot_instance: Bot):
    await bot_instance.set_my_commands([
        BotCommand(command="cake",    description="Тортик — добавить мягкость"),
        BotCommand(command="profile", description="Твой профиль"),
        BotCommand(command="top",     description="Топ мягкости"),
        BotCommand(command="rp",      description="Список RP команд"),
        BotCommand(command="give",    description="[Овнер] Дать мягкость"),
        BotCommand(command="take",    description="[Овнер] Забрать мягкость"),
        BotCommand(command="remove",  description="[Овнер] Обнулить мягкость"),
    ])

# =========================================================
# /cake
# =========================================================


@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):
    uid = m.from_user.id
    u = await db.get_user(uid, m.from_user.full_name)

    now = time.time()
    cooldown = 3600

    if now - u["last_cake"] < cooldown:
        rem = int((cooldown - (now - u["last_cake"])) / 60)
        return await m.reply(
            f"⏳ Твои щечки ещё не готовы!\n"
            f"Жди ещё <b>{rem} мин.</b>",
            parse_mode="HTML"
        )

    if uid == OWNER_ID:
        growth = random.randint(50, 120)
    else:
        growth = random.randint(5, 25)

    await db.update_softness(uid, growth)
    await db.update_last_cake(uid, now)

    u = await db.get_user(uid)

    await m.reply(
        f"🍰 <b>Мягкость щечек выросла!</b>\n"
        f"Результат: <b>+{growth} ед.</b>\n"
        f"☁️ Всего: <b>{u['softness']}</b>",
        parse_mode="HTML"
    )

# =========================================================
# /give — Овнер даёт мягкость
# =========================================================


@dp.message(Command("give"))
async def cmd_give(m: types.Message):
    if m.from_user.id != OWNER_ID:
        return

    if not m.reply_to_message:
        return await m.reply("❌ Ответь на сообщение пользователя")

    parts = m.text.split()
    if len(parts) < 2:
        return await m.reply("❌ Формат: /give 100")

    try:
        amount = int(parts[1])
    except ValueError:
        return await m.reply("❌ Укажи число: /give 100")

    target = m.reply_to_message.from_user
    await db.get_user(target.id, target.full_name)
    await db.update_softness(target.id, amount)
    u = await db.get_user(target.id)

    await m.reply(
        f"🌸 Вагурочка подарила "
        f"{target.mention_html()} "
        f"<b>+{amount}</b> мягкости!\n"
        f"☁️ Теперь у него: <b>{u['softness']}</b>",
        parse_mode="HTML"
    )

# =========================================================
# /take — Овнер забирает мягкость
# =========================================================


@dp.message(Command("take"))
async def cmd_take(m: types.Message):
    if m.from_user.id != OWNER_ID:
        return

    if not m.reply_to_message:
        return await m.reply("❌ Ответь на сообщение пользователя")

    parts = m.text.split()
    if len(parts) < 2:
        return await m.reply("❌ Формат: /take 100")

    try:
        amount = int(parts[1])
    except ValueError:
        return await m.reply("❌ Укажи число: /take 100")

    target = m.reply_to_message.from_user
    await db.get_user(target.id, target.full_name)
    await db.update_softness(target.id, -amount)
    u = await db.get_user(target.id)

    await m.reply(
        f"😈 Вагурочка забрала у "
        f"{target.mention_html()} "
        f"<b>-{amount}</b> мягкости!\n"
        f"☁️ Осталось: <b>{u['softness']}</b>",
        parse_mode="HTML"
    )

# =========================================================
# /remove — Овнер обнуляет мягкость
# =========================================================


@dp.message(Command("remove"))
async def cmd_remove(m: types.Message):
    if m.from_user.id != OWNER_ID:
        return

    if not m.reply_to_message:
        return await m.reply("❌ Ответь на сообщение пользователя")

    target = m.reply_to_message.from_user
    await db.get_user(target.id, target.full_name)
    await db.set_softness(target.id, 0)

    await m.reply(
        f"💨 Мягкость {target.mention_html()} "
        f"обнулена до <b>0</b>!",
        parse_mode="HTML"
    )

# =========================================================
# /profile
# =========================================================


@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    uid = m.from_user.id
    u = await db.get_user(uid, m.from_user.full_name)

    if uid == OWNER_ID:
        role = "👑 Создатель"
    elif await db.is_admin(uid):
        role = "🛡 Админ"
    else:
        role = "👤 Участник"

    reg = datetime.fromtimestamp(u["reg_date"]).strftime("%d.%m.%Y") if u["reg_date"] else "?"

    await m.reply(
        f"<b>『 🌸 Профиль 』</b>\n\n"
        f"👤 <b>Имя:</b> {u['name']}\n"
        f"🎖 <b>Статус:</b> {role}\n"
        f"☁️ <b>Мягкость:</b> {u['softness']} ед.\n"
        f"⚠️ <b>Варны:</b> {u['warns']}/3\n"
        f"📅 <b>В чате с:</b> {reg}",
        parse_mode="HTML"
    )

# =========================================================
# /top
# =========================================================


@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    top = await db.get_top(10)

    text = "<b>☁️ Топ Самых Мягких Щечек:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, row in enumerate(top, 1):
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        text += f"{prefix} {row['name']} — <b>{row['softness']}</b>\n"

    await m.answer(text, parse_mode="HTML")

# =========================================================
# /rp
# =========================================================


@dp.message(Command("rp"))
async def cmd_rp(m: types.Message):
    text = "<b>🌸 RP команды:</b>\n\n"
    for k in RP_MAP.keys():
        text += f"• {k}\n"
    text += "\nОтветь на сообщение и напиши действие 💬"
    await m.answer(text, parse_mode="HTML")

# =========================================================
# TEXT LOGIC
# =========================================================


@dp.message(F.text)
async def text_logic(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()

    await db.get_user(uid, m.from_user.full_name)

    # =====================================================
    # ТОРТИК (текстовый триггер)
    # =====================================================

    if txt == "тортик":
        return await cmd_cake(m)

    # =====================================================
    # РАЗБАН ПО ID (без реплая)
    # =====================================================

    if txt.startswith("разбан ") and (
        uid == OWNER_ID or await db.is_admin(uid)
    ):
        try:
            t_id = int(txt.split()[1])
            await bot.unban_chat_member(m.chat.id, t_id, only_if_banned=True)
            return await m.answer(f"🔓 Пользователь {t_id} разбанен!")
        except Exception:
            return await m.answer("❌ Формат: разбан [ID]")

    # =====================================================
    # КОМАНДЫ ЧТО ТРЕБУЮТ РЕПЛАЙ
    # =====================================================

    if not m.reply_to_message:
        return

    target = m.reply_to_message.from_user
    await db.get_user(target.id, target.full_name)

    # =====================================================
    # RP ACTIONS
    # =====================================================

    if txt in RP_MAP:
        action = RP_MAP[txt]
        caption = (
            f"🌸 {m.from_user.mention_html()} "
            f"{action['text']} "
            f"{target.mention_html()}!"
        )

        gif_sent = False
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    f"https://nekos.best/api/v2/{action['api']}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        url = data["results"][0]["url"]
                        await m.answer_animation(
                            animation=url,
                            caption=caption,
                            parse_mode="HTML"
                        )
                        gif_sent = True
        except Exception as e:
            log.warning(f"RP GIF error: {e}")

        if not gif_sent:
            await m.answer(caption, parse_mode="HTML")

        return

    # =====================================================
    # ADMIN COMMANDS
    # =====================================================

    is_adm = (uid == OWNER_ID or await db.is_admin(uid))
    if not is_adm:
        return

    try:

        # -----------------------------------------------
        # РАЗМУТ
        # -----------------------------------------------

        if txt == "размут":
            await bot.restrict_chat_member(
                m.chat.id,
                target.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            return await m.answer(f"🔊 {target.first_name} размучен!")

        # -----------------------------------------------
        # РАЗБАН (реплай)
        # -----------------------------------------------

        if txt == "разбан":
            await bot.unban_chat_member(m.chat.id, target.id, only_if_banned=True)
            return await m.answer(f"🔓 {target.first_name} разбанен!")

        # -----------------------------------------------
        # МУТ [минуты] [причина]
        # Примеры: "мут", "мут 30", "мут 60 спам"
        # -----------------------------------------------

        if txt == "мут" or txt.startswith("мут "):
            parts = m.text.lower().split(maxsplit=2)
            minutes = 15
            reason = ""

            if len(parts) >= 2:
                try:
                    minutes = int(parts[1])
                except ValueError:
                    reason = parts[1]

            if len(parts) >= 3:
                reason = parts[2]

            until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

            await bot.restrict_chat_member(
                m.chat.id,
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=until
            )

            reason_text = f"\n📝 Причина: {reason}" if reason else ""
            return await m.answer(
                f"🔇 {target.first_name} замолчал на {minutes} мин.{reason_text}"
            )

        # -----------------------------------------------
        # ВАРН [причина]
        # Примеры: "варн", "варн флуд"
        # -----------------------------------------------

        if txt == "варн" or txt.startswith("варн "):
            parts = m.text.lower().split(maxsplit=1)
            reason = parts[1] if len(parts) > 1 else ""

            t_u = await db.get_user(target.id)
            new_warns = t_u["warns"] + 1

            if new_warns >= 3:
                await bot.ban_chat_member(m.chat.id, target.id)
                await db.update_warns(target.id, 0)
                return await m.answer(
                    f"👞 {target.first_name} забанен за 3 варна!"
                )

            await db.update_warns(target.id, new_warns)
            reason_text = f"\n📝 Причина: {reason}" if reason else ""
            return await m.answer(
                f"⚠️ Варн {target.first_name}! [{new_warns}/3]{reason_text}"
            )

        # -----------------------------------------------
        # БАН
        # -----------------------------------------------

        if txt == "бан":
            await bot.ban_chat_member(m.chat.id, target.id)
            return await m.answer(f"👞 {target.first_name} изгнан!")

        # -----------------------------------------------
        # КИК
        # -----------------------------------------------

        if txt == "кик":
            await bot.ban_chat_member(m.chat.id, target.id)
            await bot.unban_chat_member(m.chat.id, target.id)
            return await m.answer(f"👞 {target.first_name} кикнут!")

        # -----------------------------------------------
        # +АДМИН (только овнер)
        # -----------------------------------------------

        if txt == "+админ" and uid == OWNER_ID:
            await db.add_admin(target.id)
            return await m.answer(f"💎 {target.first_name} теперь Админ!")

        # -----------------------------------------------
        # -АДМИН (только овнер)
        # -----------------------------------------------

        if txt == "-админ" and uid == OWNER_ID:
            await db.remove_admin(target.id)
            return await m.answer(f"🗑 {target.first_name} лишён прав Админа!")

    except Exception as e:
        log.error(f"Admin action error: {e}")
        return await m.reply(f"❌ Ошибка прав: {e}")

# =========================================================
# WELCOME
# =========================================================


@dp.message(F.new_chat_members)
async def welcome_new(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot:
            continue
        await db.get_user(mem.id, mem.full_name)
        await m.answer(
            f"🌸 Привет, {mem.mention_html()}!\n"
            f"Я Вагури. Попробуй /cake 🍰",
            parse_mode="HTML"
        )

# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================


@dp.errors()
async def global_error(update: types.Update, exception: Exception):
    log.error(f"Unhandled error | Update: {update} | Error: {exception}")
    return True

# =========================================================
# AUTO BACKUP TASK
# =========================================================


async def auto_backup_task():
    while True:
        await asyncio.sleep(1800)  # каждые 30 минут
        await db.backup(bot)

# =========================================================
# MAIN
# =========================================================


async def main():
    keep_alive()

    await db.init()

    await bot.delete_webhook(drop_pending_updates=True)

    await set_commands(bot)

    asyncio.create_task(auto_backup_task())

    log.info("Bot started polling...")

    await dp.start_polling(bot, skip_updates=True)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log.critical(f"CRITICAL ERROR: {e}")