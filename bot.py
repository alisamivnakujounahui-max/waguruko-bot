import asyncio
import random
import aiohttp
import time
import os
import logging

from threading import Thread
from datetime import timedelta, datetime
import aiosqlite

from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    ChatPermissions,
    FSInputFile
)
from aiogram.methods import GetChatHistory

# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635
BACKUP_CHANNEL = -1003866458811
DB_FILE = "waguruko_v2.db"

logging.basicConfig(level=logging.INFO)

# Хранилище для предложений брака
pending_marriages = {}

app = Flask("")

@app.route("/")
def home():
    return "🌸 Waguruko Engine: Active"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# =========================================================
# БАЗА ДАННЫХ SQLITE
# =========================================================

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uid TEXT PRIMARY KEY,
                    name TEXT,
                    softness INTEGER DEFAULT 0,
                    last_cake REAL DEFAULT 0,
                    warns INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    last_rep_give REAL DEFAULT 0,
                    status TEXT DEFAULT 'user'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS marriages (
                    user_one TEXT PRIMARY KEY,
                    user_two TEXT,
                    marriage_date TEXT
                )
            """)
            await db.commit()

    async def restore_from_tg(self, bot_instance):
        """Скачивание базы из ТГ приватного канала при перезапуске на Render"""
        try:
            chat = await bot_instance.get_chat(BACKUP_CHANNEL)
            history = await bot_instance(GetChatHistory(chat_id=chat.id, limit=30))
            
            messages = []
            if history and history.messages:
                for msg in history.messages:
                    if msg.document and msg.document.file_name == self.db_path:
                        messages.append(msg)
            
            if not messages:
                print("ℹ️ Бэкап в канале не найден, создаю новую чистую базу.")
                return
                
            latest_msg = messages[0]
            file_info = await bot_instance.get_file(latest_msg.document.file_id)
            await bot_instance.download_file(file_info.file_path, self.db_path)
            print("🌟 БАЗА ДАННЫХ УСПЕШНО ВОССТАНОВЛЕНА ИЗ КАНАЛА!")
        except Exception as e:
            print(f"❌ Ошибка восстановления базы: {e}")

    async def save_and_backup(self, bot_instance):
        try:
            if os.path.exists(self.db_path):
                await bot_instance.send_document(
                    BACKUP_CHANNEL,
                    FSInputFile(self.db_path),
                    caption=f"📦 Бэкап Вагурочки от {datetime.now().strftime('%d.%m %H:%M')}"
                )
        except Exception as e:
            print(f"Ошибка отправки бэкапа: {e}")

    async def register_user(self, uid, name):
        uid = str(uid)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT uid FROM users WHERE uid = ?", (uid,)) as cursor:
                if not await cursor.fetchone():
                    status = "owner" if int(uid) == OWNER_ID else "user"
                    await db.execute("INSERT INTO users (uid, name, status) VALUES (?, ?, ?)", (uid, name, status))
                    await db.commit()

    async def get_user(self, uid, name=None):
        uid = str(uid)
        if name:
            await self.register_user(uid, name)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET name = ? WHERE uid = ?", (name, uid))
                await db.commit()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE uid = ?", (uid,)) as cursor:
                res = await cursor.fetchone()
                if res: return dict(res)
        return {"uid": uid, "name": name or f"Юзер_{uid}", "softness": 0, "last_cake": 0, "warns": 0, "reputation": 0, "last_rep_give": 0, "status": "user"}

    async def update_user(self, uid, field, value):
        uid = str(uid)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE users SET {field} = ? WHERE uid = ?", (value, uid))
            await db.commit()

    async def get_top_softness(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT name, softness FROM users ORDER BY softness DESC LIMIT 10") as cursor:
                return await cursor.fetchall()

    async def get_top_rep(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT name, reputation FROM users ORDER BY reputation DESC LIMIT 10") as cursor:
                return await cursor.fetchall()

    async def create_marriage(self, u1, u2):
        u1, u2 = str(u1), str(u2)
        date_str = datetime.now().strftime("%d.%m.%Y")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO marriages (user_one, user_two, marriage_date) VALUES (?, ?, ?)", (u1, u2, date_str))
            await db.execute("INSERT OR REPLACE INTO marriages (user_one, user_two, marriage_date) VALUES (?, ?, ?)", (u2, u1, date_str))
            await db.commit()

    async def get_marriage(self, uid):
        uid = str(uid)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT m.user_two, m.marriage_date, u.name FROM marriages m JOIN users u ON m.user_two = u.uid WHERE m.user_one = ?", (uid,)
            ) as cursor:
                return await cursor.fetchone()

    async def get_all_marriages(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT u1.name as name1, u2.name as name2, m.marriage_date 
                FROM marriages m
                JOIN users u1 ON m.user_one = u1.uid
                JOIN users u2 ON m.user_two = u2.uid
                WHERE u1.uid < u2.uid
            """) as cursor:
                return await cursor.fetchall()

    async def divorce(self, uid):
        uid = str(uid)
        pair = await self.get_marriage(uid)
        if not pair: return False
        u2 = str(pair["user_two"])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM marriages WHERE user_one = ? OR user_one = ?", (uid, u2))
            await db.commit()
        return True

db_manager = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# СПИСОК РП КОМАНД
# =========================================================

RP_MAP = {
    "обнять": {"api": "hug", "text": "крепко обнимает", "emoji": "🫂"},
    "поцеловать": {"api": "kiss", "text": "целует в щечку", "emoji": "💋"},
    "кусь": {"api": "bite", "text": "делает кусь", "emoji": "🦷"},
    "гладить": {"api": "pat", "text": "гладит по головке", "emoji": "👋"},
    "уебать": {"api": "slap", "text": "дает пощечину", "emoji": "⚡"},
    "тык": {"api": "poke", "text": "тыкает пальчиком", "emoji": "👉"},
    "лизнуть": {"api": "lick", "text": "лизнул(а) в нос", "emoji": "👅"},
    "прижаться": {"api": "cuddle", "text": "прижимается к", "emoji": "🧸"},
    "потискать": {"api": "cuddle", "text": "тискает в объятиях", "emoji": "🐾"},
    "танцевать": {"api": "dance", "text": "танцует с", "emoji": "💃"},
    "держать": {"api": "handhold", "text": "взял(а) за руку", "emoji": "🤝"},
    "спать": {"api": "sleep", "text": "засыпает рядом с", "emoji": "💤"},
    "смущать": {"api": "blush", "text": "засмущал(а)", "emoji": "😳"},
    "кормить": {"api": "feed", "text": "кормит вкусняшкой", "emoji": "🍰"},
    "флирт": {"api": "smile", "text": "флирует с", "emoji": "✨"},
    "убить": {"api": "kick", "text": "уничтожает", "emoji": "☠️"},
    "похвалить": {"api": "highfive", "text": "хвалит и дает пять", "emoji": "🙌"},
    "ударить": {"api": "slap", "text": "бьет", "emoji": "👊"},
    "обидеться": {"api": "cry", "text": "обиделся(ась) на", "emoji": "😤"},
    "напугать": {"api": "wave", "text": "пугает из-за угла", "emoji": "👻"}
}

async def set_commands(bot_instance):
    await bot_instance.set_my_commands([
        BotCommand(command="cake", description="🧁 Съесть тортичек"),
        BotCommand(command="profile", description="🌸 Мой профиль"),
        BotCommand(command="top", description="📊 Топ по мягкости щечек"),
        BotCommand(command="top_rep", description="🎖 Топ по авторитету"),
        BotCommand(command="marriages", description="💍 Список семейных пар"),
        BotCommand(command="rp", description="📜 Все RP команды"),
        BotCommand(command="help", description="ℹ️ Справка по модерации"),
    ])

# =========================================================
# ЛОГИКА БРАКОСОЧЕТАНИЯ
# =========================================================

async def ask_marriage(m: types.Message):
    if not m.reply_to_message:
        return await m.reply("❌ Ответь словом <b>брак</b> на сообщение того, с кем хочешь построить отношения!", parse_mode="HTML")
    
    p1, p2 = m.from_user, m.reply_to_message.from_user
    if p1.id == p2.id: return await m.reply("❌ Жениться на себе нельзя, даже если очень хочется.")
    if p2.is_bot: return await m.reply("❌ Вагурочка польщена, но замуж за роботов никто не пойдет!")

    if await db_manager.get_marriage(p1.id): return await m.reply("❌ Ты уже состоишь в браке! Сначала разведись.")
    if await db_manager.get_marriage(p2.id): return await m.reply("❌ Этот человек уже занят!")

    chat_id = m.chat.id
    pending_marriages[chat_id] = {
        "proposer_id": p1.id,
        "proposer_name": p1.first_name,
        "target_id": p2.id,
        "target_name": p2.first_name,
        "time": time.time()
    }

    await m.answer(
        f"💞 <b>{p1.first_name}</b> делает предложение <b>{p2.first_name}</b>!\n"
        f"💬 Ответь на это сообщение: <code>согласен</code> или <code>согласна</code> для подтверждения (у тебя есть 60 секунд).",
        parse_mode="HTML"
    )

async def check_marriage_agreement(m: types.Message):
    chat_id = m.chat.id
    if chat_id not in pending_marriages: return

    offer = pending_marriages[chat_id]
    if time.time() - offer["time"] > 60:
        del pending_marriages[chat_id]
        return

    if m.from_user.id != offer["target_id"]: return

    txt = m.text.lower().strip()
    if txt in ["согласен", "согласна", "да"]:
        p1_id, p2_id = offer["proposer_id"], offer["target_id"]
        
        await db_manager.get_user(p1_id, offer["proposer_name"])
        await db_manager.get_user(p2_id, offer["target_name"])
        await db_manager.create_marriage(p1_id, p2_id)
        await db_manager.save_and_backup(bot)

        del pending_marriages[chat_id]
        await m.answer(f"🎉 <b>Ура! Официально!</b>\n💍 <b>{offer['proposer_name']}</b> и <b>{offer['target_name']}</b> теперь счастливая пара! Поздравляем! ✨", parse_mode="HTML")

async def show_marriages_list(m: types.Message):
    pairs = await db_manager.get_all_marriages()
    if not pairs:
        return await m.answer("💔 В этом чате пока нет ни одной супружеской пары. Все свободны!")
    
    text = "<b>💍 Зарегистрированные союзы:</b>\n"
    text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    for i, p in enumerate(pairs, 1):
        text += f"{i}. 💖 <b>{p['name1']}</b> + <b>{p['name2']}</b> (от {p['marriage_date']})\n"
    await m.answer(text, parse_mode="HTML")

# =========================================================
# СЛУШАТЕЛИ КОМАНД
# =========================================================

@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):
    u = await db_manager.get_user(m.from_user.id, m.from_user.full_name)
    now = time.time()
    if now - u["last_cake"] < 3600:
        rem = int((3600 - (now - u["last_cake"])) / 60)
        return await m.reply(f"⏳ Щечки еще не готовы! Жди <b>{rem} мин.</b>", parse_mode="HTML")
    growth = random.randint(50, 120) if m.from_user.id == OWNER_ID else random.randint(5, 25)
    new_softness = u["softness"] + growth
    await db_manager.update_user(m.from_user.id, "softness", new_softness)
    await db_manager.update_user(m.from_user.id, "last_cake", now)
    await db_manager.save_and_backup(bot)
    await m.reply(f"<b>🍰 Время тортика!</b>\n🌸 Мягкость: <b>+{growth}</b>\n☁️ Всего: <b>{new_softness} ед.</b>", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    u = await db_manager.get_user(m.from_user.id, m.from_user.full_name)
    role_map = {"owner": "👑 Создатель", "admin": "🛡 Админ", "moderator": "⚔️ Модер", "user": "👤 Юзер"}
    role = role_map.get(u["status"], "👤 Юзер")

    mar_text = "Нет пары"
    marriage = await db_manager.get_marriage(m.from_user.id)
    if marriage: mar_text = f"💍 С {marriage['name']}"

    text = (
        f"<b>🌸 Профиль Вагурочки</b>\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👤 <b>Имя:</b> {u['name']}\n"
        f"🎖 <b>Ранг:</b> {role}\n"
        f"☁️ <b>Мягкость:</b> {u['softness']} ед.\n"
        f"⭐ <b>Авторитет:</b> {u['reputation']} ⭐\n"
        f"⚠️ <b>Варны:</b> {u['warns']}/3\n"
        f"❤️ <b>Брак:</b> {mar_text}"
    )
    await m.reply(text, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    top_list = await db_manager.get_top_softness()
    text = "<b>📊 Самые мягкие щечки:</b>\n"
    for i, row in enumerate(top_list, 1): text += f"{i}. {row['name']} — <b>{row['softness']}</b>\n"
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("top_rep"))
async def cmd_top_rep(m: types.Message):
    top_list = await db_manager.get_top_rep()
    text = "<b>🎖 Топ авторитетов чата:</b>\n"
    for i, row in enumerate(top_list, 1): text += f"{i}. {row['name']} — <b>{row['reputation']}</b> ⭐\n"
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("marriages"))
async def cmd_marriages_list(m: types.Message): await show_marriages_list(m)

@dp.message(Command("rp"))
async def cmd_rp(m: types.Message):
    text = "<b>📜 Ролевые команды (реплаем):</b>\n\n"
    for cmd, info in RP_MAP.items(): text += f"• <code>{cmd}</code> {info['emoji']}\n"
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    text = (
        f"<b>⚔️ Модерация (текстом в ответ):</b>\n"
        f"• <code>варн</code> — дать варн\n"
        f"• <code>мут [время] [м/ч/д]</code> — пример: <i>мут 10 м</i>\n"
        f"• <code>размут</code> — снять мут\n"
        f"• <code>кик</code> / <code>бан</code>\n\n"
        f"<b>💍 Отношения:</b>\n"
        f"• <code>брак</code> (в ответ) — предложить союз\n"
        f"• <code>пары</code> — список женатых\n"
        f"• <code>развод</code> — расторгнуть союз"
    )
    await m.reply(text, parse_mode="HTML")

# =========================================================
# ТЕКСТОВАЯ ЛОГИКА
# =========================================================

@dp.message(F.text)
async def text_logic(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()

    u_sender = await db_manager.get_user(uid, m.from_user.full_name)

    if txt in ["согласен", "согласна", "да"] and m.reply_to_message:
        await check_marriage_agreement(m)
        return

    if txt == "тортик":
        u = await db_manager.get_user(m.from_user.id, m.from_user.full_name)
        now = time.time()
        if now - u["last_cake"] < 3600: return await m.reply(f"⏳ Жди {int((3600-(now-u['last_cake']))/60)} мин.")
        growth = random.randint(50, 120) if uid == OWNER_ID else random.randint(5, 25)
        await db_manager.update_user(uid, "softness", u["softness"]+growth)
        await db_manager.update_user(uid, "last_cake", now)
        await db_manager.save_and_backup(bot)
        return await m.reply(f"🍰 Мягкость: +{growth} (Всего: {u['softness']+growth})")

    if txt == "брак":
        await ask_marriage(m)
        return

    if txt in ["пары", "список пар", "браки"]:
        await show_marriages_list(m)
        return

    if txt == "развод":
        if await db_manager.divorce(uid):
            await db_manager.save_and_backup(bot)
            await m.reply("💔 Брак расторгнут. Ты снова в поиске.")
        else:
            await m.reply("❌ Ты не состоишь в браке.")
        return

    if txt.startswith("разбан ") and (u_sender["status"] in ["admin", "owner"] or uid == OWNER_ID):
        try:
            target_id = int(m.text.split()[1])
            await bot.unban_chat_member(m.chat.id, target_id, only_if_banned=True)
            return await m.answer(f"🔓 Пользователь {target_id} разбанен.")
        except: return

    if not m.reply_to_message: return

    target = m.reply_to_message.from_user
    t_u = await db_manager.get_user(target.id, target.full_name)

    if txt in ["+", "респект", "спс", "спасибо", "лайк"]:
        if uid == target.id: return
        now = time.time()
        if now - u_sender["last_rep_give"] < 60: return await m.reply("⏱ Плюсовать можно раз в минуту!")
        new_rep = t_u["reputation"] + 1
        await db_manager.update_user(target.id, "reputation", new_rep)
        await db_manager.update_user(uid, "last_rep_give", now)
        await db_manager.save_and_backup(bot)
        return await m.reply(f"⭐️ {m.from_user.first_name} поднял авторитет {target.first_name}! (Всего: <b>{new_rep}</b>)", parse_mode="HTML")

    if txt in RP_MAP:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://nekos.best/api/v2/{RP_MAP[txt]['api']}") as r:
                    data = await r.json()
                    await m.answer_animation(
                        animation=data["results"][0]["url"],
                        caption=f"{RP_MAP[txt]['emoji']} <b>{m.from_user.first_name}</b> {RP_MAP[txt]['text']} <b>{target.first_name}</b>!",
                        parse_mode="HTML"
                    )
                    return
        except:
            await m.answer(f"{RP_MAP[txt]['emoji']} <b>{m.from_user.first_name}</b> {RP_MAP[txt]['text']} <b>{target.first_name}</b>!", parse_mode="HTML")
            return

    is_mod = u_sender["status"] in ["moderator", "admin", "owner"] or uid == OWNER_ID
    if not is_mod: return

    try:
        if txt == "варн":
            new_warns = t_u["warns"] + 1
            if new_warns >= 3:
                await bot.ban_chat_member(m.chat.id, target.id)
                await db_manager.update_user(target.id, "warns", 0)
                await db_manager.save_and_backup(bot)
                return await m.answer(f"❌ {target.first_name} набрал 3/3 варнов и отправлен в бан.")
            await db_manager.update_user(target.id, "warns", new_warns)
            await db_manager.save_and_backup(bot)
            return await m.answer(f"⚠️ {target.first_name} получает варн! [<b>{new_warns}/3</b>]", parse_mode="HTML")

        if txt.startswith("мут"):
            duration = timedelta(minutes=15)
            parts = txt.split()
            if len(parts) >= 3:
                try:
                    val = int(parts[1])
                    unit = parts[2]
                    if "м" in unit: duration = timedelta(minutes=val)
                    elif "ч" in unit: duration = timedelta(hours=val)
                    elif "д" in unit: duration = timedelta(days=val)
                except: pass
            await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=duration)
            return await m.answer(f"🔇 {target.first_name} заглушен на {duration.total_seconds()//60:.0f} мин.")

        if txt == "размут":
            await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            return await m.answer(f"🔊 {target.first_name} снова может говорить.")

        if txt == "кик":
            await bot.ban_chat_member(m.chat.id, target.id)
            await bot.unban_chat_member(m.chat.id, target.id)
            return await m.answer(f"👞 {target.first_name} кикнут.")

        if txt == "бан":
            await bot.ban_chat_member(m.chat.id, target.id)
            return await m.answer(f"🚷 {target.first_name} забанен.")

        if uid == OWNER_ID:
            if txt == "+админ":
                await db_manager.update_user(target.id, "status", "admin")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"👑 {target.first_name} теперь Администратор.")
            if txt in ["-админ", "-модер"]:
                await db_manager.update_user(target.id, "status", "user")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"👤 {target.first_name} разжалован.")
            if txt == "+модер":
                await db_manager.update_user(target.id, "status", "moderator")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"🛡 {target.first_name} назначен Модератором.")
    except Exception as e:
        print(f"Ошибка прав: {e}")

# =========================================================
# ЗАПУСК
# =========================================================

@dp.message(F.new_chat_members)
async def welcome_bot(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot: continue
        await db_manager.get_user(mem.id, mem.full_name)
        await m.answer(f"🌸 Привет, {mem.first_name}! Я Вагурочка. Напиши слово <code>тортик</code> 🍰", parse_mode="HTML")

async def main():
    keep_alive()
    
    # 1. Сначала инициализируем структуру таблиц в локальном файле
    await db_manager.init_db()
    
    try:
        # 2. Сбрасываем старые зависшие сессии, убирая TelegramConflictError
        await bot.delete_webhook(drop_pending_updates=True)
        print("🧹 Старые сессии Telegram сброшены.")
        
        # 3. Восстанавливаем базу данных из приватного ТГ-канала
        print("🔄 Попытка восстановить базу данных из Telegram...")
        await db_manager.restore_from_tg(bot)
        
    except Exception as e:
        print(f"⚠️ Ошибка на этапе подготовки базы: {e}")

    # 4. Настраиваем кнопки команд меню
    await set_commands(bot)
    
    # 5. Включаем постоянное чтение чатов
    print("🚀 Вагурочка успешно запустила лонг-поллинг!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())