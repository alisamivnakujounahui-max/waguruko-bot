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

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7799004635
BACKUP_CHANNEL = -1003866458811

# Локальное имя файла базы данных на сервере Render
DB_FILE = "waguruko_v2.db"

logging.basicConfig(level=logging.INFO)

# =========================================================
# FLASK KEEP ALIVE
# =========================================================

app = Flask("")

@app.route("/")
def home():
    return "🌸 Waguruko Engine 2.0: Free & Cloud Active"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# =========================================================
# ASYNC SQLITE DATABASE (Waguruko Engine 2.0 + Auto TG Cloud)
# =========================================================

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    async def init_db(self):
        """Создает таблицы, если их нет"""
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
            print(f"⚙️ SQLite база данных успешно инициализирована.")

    # --- СВЕРХВАЖНО: Скачивание базы из ТГ при перезапуске на Render ---
    async def restore_from_tg(self, bot_instance):
        try:
            print("🔄 Попытка восстановить базу данных из Telegram...")
            messages = []
            async for msg in bot_instance.get_chat_history(BACKUP_CHANNEL, limit=30):
                if msg.document and msg.document.file_name == self.db_path:
                    messages.append(msg)

            if not messages:
                print("⚠️ Бэкап в канале не найден. Создаем чистую базу данных.")
                return

            # Берем самое последнее сообщение с файлом
            latest_msg = messages[0]
            file_info = await bot_instance.get_file(latest_msg.document.file_id)
            
            # Скачиваем файл на Render, перезаписывая пустой локальный файл
            await bot_instance.download_file(file_info.file_path, self.db_path)
            print("🌟 БАЗА ДАННЫХ УСПЕШНО ВОССТАНОВЛЕНА ИЗ TELEGRAM CLOUD!")
        except Exception as e:
            print(f"❌ Ошибка восстановления базы из ТГ: {e}")

    # --- СВЕРХВАЖНО: Авто-выгрузка файла базы в ТГ при изменениях ---
    async def save_and_backup(self, bot_instance):
        try:
            if os.path.exists(self.db_path):
                await bot_instance.send_document(
                    BACKUP_CHANNEL,
                    FSInputFile(self.db_path),
                    caption=f"📦 Обновление облака базы данных SQLite\n📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print("☁️ Копия базы успешно отправлена в твой Telegram-канал.")
        except Exception as e:
            print(f"❌ Ошибка отправки бэкапа в ТГ: {e}")

    async def register_user(self, uid, name):
        uid = str(uid)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT uid FROM users WHERE uid = ?", (uid,)) as cursor:
                if not await cursor.fetchone():
                    status = "owner" if int(uid) == OWNER_ID else "user"
                    await db.execute(
                        "INSERT INTO users (uid, name, status) VALUES (?, ?, ?)",
                        (uid, name, status)
                    )
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
                if res:
                    return dict(res)
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
                "SELECT m.user_two, m.marriage_date, u.name FROM marriages m JOIN users u ON m.user_two = u.uid WHERE m.user_one = ?", 
                (uid,)
            ) as cursor:
                return await cursor.fetchone()

    async def divorce(self, uid):
        uid = str(uid)
        pair = await self.get_marriage(uid)
        if not pair:
            return False
        u2 = str(pair["user_two"])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM marriages WHERE user_one = ? OR user_one = ?", (uid, u2))
            await db.commit()
        return True

db_manager = Database(DB_FILE)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# РАСШИРЕННАЯ КАРТА RP-КОМАНД (Версия 2.0)
# =========================================================

RP_MAP = {
    "обнять": {"api": "hug", "text": "крепко-крепко обнимает", "emoji": "🫂"},
    "поцеловать": {"api": "kiss", "text": "нежно целует в щечку", "emoji": "💋"},
    "кусь": {"api": "bite", "text": "делает игривый кусь", "emoji": "🦷"},
    "гладить": {"api": "pat", "text": "ласково гладит по головке", "emoji": "👋"},
    "уебать": {"api": "slap", "text": "дает звонкую пощечину", "emoji": "⚡"},
    "тык": {"api": "poke", "text": "аккуратно тыкает пальчиком в бок", "emoji": "👉"},
    "лизнуть": {"api": "lick", "text": "лизнул(а) прямо в нос", "emoji": "👅"},
    "прижаться": {"api": "cuddle", "text": "мило прижимается к", "emoji": "🧸"},
    "потискать": {"api": "cuddle", "text": "затискивает в объятиях", "emoji": "🐾"},
    "танцевать": {"api": "dance", "text": "кружится в быстром танце с", "emoji": "💃"},
    "держать": {"api": "handhold", "text": "берет за теплую руку", "emoji": "🤝"},
    "спать": {"api": "sleep", "text": "укладывается спать рядышком с", "emoji": "💤"},
    "смущать": {"api": "blush", "text": "заставляет сильно покраснеть", "emoji": "😳"},
    "кормить": {"api": "feed", "text": "угощает вкусняшкой и кормит с ложечки", "emoji": "🍰"},
    "флирт": {"api": "smile", "text": "строит глазки и флиртует с", "emoji": "✨"},
    "убить": {"api": "kick", "text": "стирает в порошок", "emoji": "☠️"},
    "похвалить": {"api": "highfive", "text": "искренне хвалит и дает пять", "emoji": "🙌"},
    "ударить": {"api": "slap", "text": "наносит сокрушительный удар", "emoji": "👊"},
    "обидеться": {"api": "cry", "text": "надул(а) губки и отвернулся(ась) от", "emoji": "😤"},
    "напугать": {"api": "wave", "text": "выскакивает из-за угла и пугает", "emoji": "👻"}
}

# =========================================================
# BOT COMMANDS SETUP
# =========================================================

async def set_commands(bot_instance):
    await bot_instance.set_my_commands([
        BotCommand(command="cake", description="🧁 Сьесть ежедневный тортик"),
        BotCommand(command="profile", description="🌸 Посмотреть свой профиль"),
        BotCommand(command="top", description="📊 Топ по мягкости щечек"),
        BotCommand(command="top_rep", description="🎖 Топ по авторитету/репутации"),
        BotCommand(command="rp", description="📜 Список всех доступных RP-действий"),
        BotCommand(command="marry", description="💍 Предложить брак (ответом на смс)"),
        BotCommand(command="divorce", description="💔 Расторгнуть текущий брак"),
        BotCommand(command="help", description="ℹ️ Полная справка по командам модерации"),
    ])

# =========================================================
# USER COMMANDS
# =========================================================

@dp.message(Command("cake"))
async def cmd_cake(m: types.Message):
    u = await db_manager.get_user(m.from_user.id, m.from_user.full_name)
    now = time.time()

    if now - u["last_cake"] < 3600:
        rem = int((3600 - (now - u["last_cake"])) / 60)
        return await m.reply(f"⏳ <b>Твои щечки еще не проголодались!</b>\nПриходи через <b>{rem} мин.</b> 💤", parse_mode="HTML")

    growth = random.randint(50, 120) if m.from_user.id == OWNER_ID else random.randint(5, 25)
    new_softness = u["softness"] + growth

    await db_manager.update_user(m.from_user.id, "softness", new_softness)
    await db_manager.update_user(m.from_user.id, "last_cake", now)
    
    # Пушим в облако ТГ
    await db_manager.save_and_backup(bot)

    await m.reply(
        f"<b>『 🍰 Время Тортика! 』</b>\n\n"
        f"🌸 {m.from_user.mention_html()}, ты скушал(а) вкусный десерт!\n"
        f"✨ Твои щечки округлились на: <b>+{growth} ед.</b>\n"
        f"☁️ Общая воздушность: <b>{new_softness} ед.</b>",
        parse_mode="HTML"
    )

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    u = await db_manager.get_user(m.from_user.id, m.from_user.full_name)
    
    role_map = {"owner": "👑 Создатель", "admin": "🛡 Администратор", "moderator": "⚔️ Модератор чата", "user": "👤 Участник чата"}
    role = role_map.get(u["status"], "👤 Участник чата")

    marriage_text = "🚪 Не состоит в отношениях"
    marriage = await db_manager.get_marriage(m.from_user.id)
    if marriage:
        marriage_text = f"💍 В браке с <b>{marriage['name']}</b> (от {marriage['marriage_date']})"

    text = (
        f"<b>『 🌸 Информационная Карта Юзера 』</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Имя:</b> {u['name']}\n"
        f"🆔 <b>ID:</b> <code>{u['uid']}</code>\n"
        f"🎖 <b>Ранг:</b> <code>{role}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"☁️ <b>Мягкость Щёчек:</b> <code>{u['softness']} ед.</code>\n"
        f"⭐ <b>Репутация/Авторитет:</b> <code>{u['reputation']} ⭐</code>\n"
        f"⚠️ <b>Предупреждения:</b> <code>{u['warns']}/3</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ <b>Статус:</b> {marriage_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await m.reply(text, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(m: types.Message):
    top_list = await db_manager.get_top_softness()
    text = "<b>📊 『 Топ Самых Мягких Щёчек Чат-Менеджера 』</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, row in enumerate(top_list, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"<code>{i}.</code>"
        text += f"{medal} {row['name']} — <b>{row['softness']}</b> ☁️\n"
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("top_rep"))
async def cmd_top_rep(m: types.Message):
    top_list = await db_manager.get_top_rep()
    text = "<b>🎖 『 Топ Уважаемых и Авторитетных Людей 』</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, row in enumerate(top_list, 1):
        medal = "👑" if i == 1 else "⭐️"
        text += f"{i}. {row['name']} — <b>{row['reputation']}</b> {medal}\n"
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("rp"))
async def cmd_rp(m: types.Message):
    text = "<b>📜 『 Реестр Доступных Ролевых Команд 』</b>\n\n"
    text += "<i>Напишите кодовое слово в ответ на сообщение игрока:</i>\n\n"
    for cmd, info in RP_MAP.items():
        text += f"▪️ <b>{cmd}</b> — {info['emoji']} <code>{info['text']}</code>\n"
    await m.answer(text, parse_mode="HTML")

# =========================================================
# СИСТЕМА БРАКОВ
# =========================================================

@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message:
        return await m.reply("❌ <b>Команда пишется в ответ на сообщение того, с кем хочешь создать семью!</b>", parse_mode="HTML")
    
    proposer = m.from_user
    partner = m.reply_to_message.from_user

    if proposer.id == partner.id:
        return await m.reply("❌ Жениться на самом себе нельзя!", parse_mode="HTML")

    m1 = await db_manager.get_marriage(proposer.id)
    m2 = await db_manager.get_marriage(partner.id)

    if m1: return await m.reply("❌ Ты уже состоишь в браке! Сначала разведись.", parse_mode="HTML")
    if m2: return await m.reply("❌ Этот человек уже женат/замужем!", parse_mode="HTML")

    await db_manager.get_user(proposer.id, proposer.full_name)
    await db_manager.get_user(partner.id, partner.full_name)
    
    await db_manager.create_marriage(proposer.id, partner.id)
    await db_manager.save_and_backup(bot)

    await m.answer(
        f"<b>💍 『 СВЯЩЕННЫЙ СОЮЗ ЗАКЛЮЧЕН 』</b>\n\n"
        f"🎉 {proposer.mention_html()} и {partner.mention_html()} "
        f"теперь официально объявили себя парой!\n"
        f"💖 Желаем бесконечной мягкости вам!",
        parse_mode="HTML"
    )

@dp.message(Command("divorce"))
async def cmd_divorce(m: types.Message):
    success = await db_manager.divorce(m.from_user.id)
    if success:
        await db_manager.save_and_backup(bot)
        await m.reply("<b>💔 Развод оформлен.</b> Ты снова в поиске.", parse_mode="HTML")
    else:
        await m.reply("❌ Ты и так не в браке!", parse_mode="HTML")

# =========================================================
# СПРАВКА МОДЕРАЦИИ (Iris-Style)
# =========================================================

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    help_text = (
        f"<b>📌 Справка по Командам Модерации Iris-Style</b>\n"
        f"<i>Пишутся текстом в ответ на сообщение нарушителя:</i>\n\n"
        f"⚠️ <b>варн</b> — Выдать предупреждение (+1 к счетчику)\n"
        f"🔇 <b>мут [время] [м/ч/д]</b> — Пример: <code>мут 10 м</code>, <code>мут 2 ч</code>\n"
        f"🔊 <b>размут</b> — Снять заглушку\n"
        f"👞 <b>кик</b> — Исключить из чата\n"
        f"🚷 <b>бан</b> — Забанить в группе\n"
        f"🔓 <b>разбан [ID]</b> — Снять бан по ID\n\n"
        f"<b>⚙️ Админка (Только Создатель):</b>\n"
        f"➕ <b>+админ</b> / ➖ <b>-админ</b>\n"
        f"➕ <b>+модер</b> / ➖ <b>-модер</b>\n\n"
        f"<b>⭐️ Репутация:</b>\n"
        f"В ответ на смс отправь: + / респект / спс"
    )
    await m.reply(help_text, parse_mode="HTML")

# =========================================================
# ТЕКСТОВАЯ ЛОГИКА И АВТО-МОДЕРАЦИЯ
# =========================================================

@dp.message(F.text)
async def text_logic(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()

    u_sender = await db_manager.get_user(uid, m.from_user.full_name)

    if txt == "тортик":
        return await cmd_cake(m)

    # Разбан по тексту по ID: "разбан 123456"
    if txt.startswith("разбан ") and (u_sender["status"] in ["admin", "owner"] or uid == OWNER_ID):
        try:
            target_id = int(m.text.split()[1])
            await bot.unban_chat_member(m.chat.id, target_id, only_if_banned=True)
            return await m.answer(f"<b>🔓 Разблокировка:</b> ID {target_id} амнистирован.", parse_mode="HTML")
        except:
            return await m.answer("❌ Формат: <code>разбан [ID]</code>", parse_mode="HTML")

    if not m.reply_to_message:
        return

    target = m.reply_to_message.from_user
    t_u = await db_manager.get_user(target.id, target.full_name)

    # --- РЕПУТАЦИЯ ---
    if txt in ["+", "респект", "спс", "спасибо", "лайк"]:
        if uid == target.id:
            return await m.reply("❌ Нельзя повышать репутацию самому себе!", parse_mode="HTML")
        
        now = time.time()
        if now - u_sender["last_rep_give"] < 60:
            return await m.reply("⏱ Ограничение! Повышать авторитет можно раз в минуту.", parse_mode="HTML")
        
        new_rep = t_u["reputation"] + 1
        await db_manager.update_user(target.id, "reputation", new_rep)
        await db_manager.update_user(uid, "last_rep_give", now)
        await db_manager.save_and_backup(bot)

        return await m.reply(
            f"⭐️ <b>Репутация повышена!</b>\n"
            f"{m.from_user.mention_html()} поднял авторитет {target.mention_html()}!\n"
            f"📈 Всего репутации: <b>{new_rep} ⭐</b>",
            parse_mode="HTML"
        )

    # --- АНИМАЦИИ (RP КОМАНДЫ) ---
    if txt in RP_MAP:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://nekos.best/api/v2/{RP_MAP[txt]['api']}") as r:
                    data = await r.json()
                    gif_url = data["results"][0]["url"]

                    await m.answer_animation(
                        animation=gif_url,
                        caption=(
                            f"{RP_MAP[txt]['emoji']} <b>{m.from_user.mention_html()}</b> "
                            f"{RP_MAP[txt]['text']} <b>{target.mention_html()}</b>!"
                        ),
                        parse_mode="HTML"
                    )
                    return
        except Exception:
            await m.answer(
                f"{RP_MAP[txt]['emoji']} <b>{m.from_user.first_name}</b> "
                f"{RP_MAP[txt]['text']} <b>{target.first_name}</b>!",
                parse_mode="HTML"
            )
            return

    # --- ПРОВЕРКА ПРАВ МОДЕРАЦИИ ---
    is_mod = u_sender["status"] in ["moderator", "admin", "owner"] or uid == OWNER_ID
    if not is_mod:
        return

    try:
        # ВАРН
        if txt == "варн":
            new_warns = t_u["warns"] + 1
            if new_warns >= 3:
                await bot.ban_chat_member(m.chat.id, target.id)
                await db_manager.update_user(target.id, "warns", 0)
                await db_manager.save_and_backup(bot)
                return await m.answer(f"❌ <b>Наказание:</b> {target.mention_html()} набрал [3/3] варнов и забанен!", parse_mode="HTML")
            
            await db_manager.update_user(target.id, "warns", new_warns)
            await db_manager.save_and_backup(bot)
            return await m.answer(f"⚠️ <b>Варн!</b> {target.mention_html()} получает предупреждение. [<b>{new_warns}/3</b>]", parse_mode="HTML")

        # МУТ IRIS-STYLE ("мут 10 м", "мут 5 ч", "мут 1 д")
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
                except ValueError: pass

            await bot.restrict_chat_member(m.chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=duration)
            return await m.answer(f"🔇 <b>Мут:</b> {target.mention_html()} заглушен на <b>{duration.total_seconds()//60:.0f} мин.</b>", parse_mode="HTML")

        # РАЗМУТ
        if txt == "размут":
            await bot.restrict_chat_member(
                m.chat.id, target.id,
                ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
            )
            return await m.answer(f"🔊 {target.mention_html()} размучен модератором.", parse_mode="HTML")

        # КИК
        if txt == "кик":
            await bot.ban_chat_member(m.chat.id, target.id)
            await bot.unban_chat_member(m.chat.id, target.id)
            return await m.answer(f"👞 Пользователь {target.mention_html()} кикнут.", parse_mode="HTML")

        # БАН
        if txt == "бан":
            await bot.ban_chat_member(m.chat.id, target.id)
            return await m.answer(f"🚷 {target.mention_html()} заблокирован в чате.", parse_mode="HTML")

        # НАЗНАЧЕНИЕ ДОЛЖНОСТЕЙ СОЗДАТЕЛЕМ
        if uid == OWNER_ID:
            if txt == "+админ":
                await db_manager.update_user(target.id, "status", "admin")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"👑 {target.mention_html()} назначен Администратором бота!", parse_mode="HTML")
            if txt in ["-админ", "-модер"]:
                await db_manager.update_user(target.id, "status", "user")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"👤 {target.mention_html()} разжалован до обычного юзера.", parse_mode="HTML")
            if txt == "+модер":
                await db_manager.update_user(target.id, "status", "moderator")
                await db_manager.save_and_backup(bot)
                return await m.answer(f"🛡 {target.mention_html()} назначен Модератором чата.", parse_mode="HTML")

    except Exception as e:
        return await m.reply(f"❌ Ошибка прав: проверьте админку бота.\n<code>{e}</code>", parse_mode="HTML")

# =========================================================
# ВХОД В ЧАТ
# =========================================================

@dp.message(F.new_chat_members)
async def welcome_bot(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot: continue
        await db_manager.get_user(mem.id, mem.full_name)
        await m.answer(
            f"🌸 <b>Добро пожаловать, {mem.mention_html()}!</b>\n"
            f"Я бот Вагури. С нами весело! Попробуй написать слово <code>тортик</code> 🍰",
            parse_mode="HTML"
        )

# =========================================================
# ЗАПУСК И ВОССТАНОВЛЕНИЕ
# =========================================================

async def main():
    keep_alive()

    # Сначала создаем пустые таблицы (если файла вообще нет на сервере)
    await db_manager.init_db()

    # КЛЮЧЕВОЙ МОМЕНТ: качаем актуальную базу данных из ТГ-канала наружу перед запуском бота
    await db_manager.restore_from_tg(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL FAULT: {e}")