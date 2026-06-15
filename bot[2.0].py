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
from aiogram.filters import Command, CommandObject
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

# Если на Render подключен Диск, данные будут жить в /data/waguruko_v2.db
# Если диска нет, создастся в папке с ботом.
DB_DIR = "/data" if os.path.exists("/data") else "."
DB_FILE = os.path.join(DB_DIR, "waguruko_v2.db")

logging.basicConfig(level=logging.INFO)

# =========================================================
# FLASK KEEP ALIVE
# =========================================================

app = Flask("")

@app.route("/")
def home():
    return "🌸 Waguruko Engine 2.0: Core Active"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# =========================================================
# ASYNC SQLITE DATABASE (Waguruko Engine 2.0)
# =========================================================

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    async def init_db(self):
        """Создает таблицы, если их нет в базе данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
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
            # Таблица браков
            await db.execute("""
                CREATE TABLE IF NOT EXISTS marriages (
                    user_one TEXT PRIMARY KEY,
                    user_two TEXT,
                    marriage_date TEXT
                )
            """)
            await db.commit()
            print(f"⚙️ SQLite база данных успешно инициализирована: {self.db_path}")

    async def register_user(self, uid, name):
        uid = str(uid)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT uid FROM users WHERE uid = ?", (uid,)) as cursor:
                if not await cursor.fetchone():
                    # Создатель получает статус owner автоматически
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
            # Обновим имя, если изменилось
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

    # --- Логика Браков ---
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

    # --- Аварийный бэкап файла базы данных в Telegram ---
    async def backup_db_file(self, bot_instance):
        try:
            if os.path.exists(self.db_path):
                await bot_instance.send_document(
                    BACKUP_CHANNEL,
                    FSInputFile(self.db_path),
                    caption=f"📦 Накатан плановый бэкап базы данных SQLite\n📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print("🌟 Файл базы данных успешно зарезервирован в ТГ-канале.")
        except Exception as e:
            print(f"Ошибка отправки файла бэкапа: {e}")

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
    # Новые команды версии 2.0
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
# USER COMMANDS (Развлечения / Профиль / Свадьбы)
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
    
    role_map = {"owner": "👑 Создатель", "admin": "🛡 Администратор", "user": "👤 Участник чата"}
    role = role_map.get(u["status"], "👤 Участник чата")

    # Проверка брака
    marriage_text = "🚪 Не состоит в отношениях"
    marriage = await db_manager.get_marriage(m.from_user.id)
    if marriage:
        marriage_text = f"💍 В браке с <b>{marriage['name']}</b> (от {marriage['marriage_date']})"

    text = (
        f"<b>『 🌸 Информационная Карта Юзера 』</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Имя:</b> {u['name']}\n"
        f"🆔 <b>Твой ID:</b> <code>{u['uid']}</code>\n"
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
    text += "<i>Чтобы применить, напишите кодовое слово в ответ (reply) на сообщение игрока:</i>\n\n"
    for cmd, info in RP_MAP.items():
        text += f"▪️ <b>{cmd}</b> — {info['emoji']} <code>{info['text']}</code>\n"
    await m.answer(text, parse_mode="HTML")

# =========================================================
# СИСТЕМА БРАКОВ (Новый функционал)
# =========================================================

@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message:
        return await m.reply("❌ <b>Команда пишется в ответ на сообщение того, с кем хочешь создать семью!</b>", parse_mode="HTML")
    
    proposer = m.from_user
    partner = m.reply_to_message.from_user

    if proposer.id == partner.id:
        return await m.reply("❌ Жениться на самом себе? Хм, звучит одиноко...", parse_mode="HTML")

    # Проверим, не женат ли уже кто-то
    m1 = await db_manager.get_marriage(proposer.id)
    m2 = await db_manager.get_marriage(partner.id)

    if m1:
        return await m.reply("❌ Ты уже состоишь в законном браке! Сначала разведись.", parse_mode="HTML")
    if m2:
        return await m.reply("❌ Этот человек уже занят кем-то другим. Не разрушай семью!", parse_mode="HTML")

    # Создаем запись
    await db_manager.get_user(proposer.id, proposer.full_name)
    await db_manager.get_user(partner.id, partner.full_name)
    await db_manager.create_marriage(proposer.id, partner.id)

    await m.answer(
        f"<b>💍 『 СВЯЩЕННЫЙ СОЮЗ ЗАКЛЮЧЕН 』</b>\n\n"
        f"🎉 Свидетели, ликуйте! {proposer.mention_html()} и {partner.mention_html()} "
        f"теперь официально объявили себя парой!\n"
        f"💖 Желаем бесконечной мягкости и сладких тортиков вам!",
        parse_mode="HTML"
    )

@dp.message(Command("divorce"))
async def cmd_divorce(m: types.Message):
    success = await db_manager.divorce(m.from_user.id)
    if success:
        await m.reply("<b>💔 Развод оформлен.</b> Сердце разбито, кольца сданы в ломбард... Ты снова в поиске.", parse_mode="HTML")
    else:
        await m.reply("❌ Ты и так птица вольная, расторгать нечего!", parse_mode="HTML")

# =========================================================
# СПРАВКА И МОДЕРАЦИЯ ПО КОМАНДАМ (Iris-Style)
# =========================================================

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    help_text = (
        f"<b>📌 Справка по Командам Модерации Iris-Style</b>\n"
        f"<i>Пишутся текстом в ответ на сообщение нарушителя:</i>\n\n"
        f"⚠️ <b>варн</b> — Выдать предупреждение (+1 к счетчику)\n"
        f"🔇 <b>мут [время]</b> — Заглушить. Примеры: <code>мут 10 м</code>, <code>мут 2 ч</code>, <code>мут 1 д</code>\n"
        f"🔊 <b>размут</b> — Снять заглушку досрочно\n"
        f"👞 <b>кик</b> — Исключить пользователя из чата\n"
        f"🚷 <b>бан</b> — Навсегда заблокировать в группе\n"
        f"🔓 <b>разбан</b> — Снять бан (можно текстом 'разбан ID' в чат)\n\n"
        f"<b>⚙️ Управление правами (Только Создатель):</b>\n"
        f"➕ <b>+админ</b> — Выдать статус Администратора бота\n"
        f"➖ <b>-админ</b> — Разжаловать администратора\n"
        f"➕ <b>+модер</b> — Назначить локального модератора чата\n\n"
        f"<b>⭐️ Дополнительно (Для всех):</b>\n"
        f"👍 / Респект / + / Спс — Поднять репутацию пользователю в ответе"
    )
    await m.reply(help_text, parse_mode="HTML")

# =========================================================
# ОБРАБОТЧИК ТЕКСТОВЫХ И МОДЕРАТОРСКИХ КОМАНД
# =========================================================

@dp.message(F.text)
async def text_logic(m: types.Message):
    uid = m.from_user.id
    txt = m.text.lower().strip()

    # Авто-регистрация говорящего
    u_sender = await db_manager.get_user(uid, m.from_user.full_name)

    # Быстрый триггер на "тортик"
    if txt == "тортик":
        return await cmd_cake(m)

    # -----------------------------------------------------
    # Разбан по ID текстом: "разбан 12345678"
    # -----------------------------------------------------
    if txt.startswith("разбан ") and (u_sender["status"] in ["admin", "owner"] or uid == OWNER_ID):
        try:
            target_id = int(m.text.split()[1])
            await bot.unban_chat_member(m.chat.id, target_id, only_if_banned=True)
            return await m.answer(f"<b>🔓 Разблокировка:</b> ID {target_id} успешно амнистирован в системе.", parse_mode="HTML")
        except:
            return await m.answer("❌ Сбой синтаксиса. Шаблон: <code>разбан [ID_ПОЛЬЗОВАТЕЛЯ]</code>", parse_mode="HTML")

    # -----------------------------------------------------
    # Если это НЕ ответ на сообщение — прерываемся
    # -----------------------------------------------------
    if not m.reply_to_message:
        return

    target = m.reply_to_message.from_user
    t_u = await db_manager.get_user(target.id, target.full_name)

    # -----------------------------------------------------
    # СИСТЕМА РЕПУТАЦИИ (лайки ответом на пост)
    # -----------------------------------------------------
    if txt in ["+", "респект", "спс", "спасибо", "лайк"]:
        if uid == target.id:
            return await m.reply("❌ Нельзя повышать репутацию самому себе!", parse_mode="HTML")
        
        now = time.time()
        if now - u_sender["last_rep_give"] < 60:
            return await m.reply("⏱ Повышать авторитет можно не чаще, чем раз в минуту!", parse_mode="HTML")
        
        new_rep = t_u["reputation"] + 1
        await db_manager.update_user(target.id, "reputation", new_rep)
        await db_manager.update_user(uid, "last_rep_give", now)

        return await m.reply(
            f"⭐️ <b>Репутация повышена!</b>\n"
            f"{m.from_user.mention_html()} выразил уважение {target.mention_html()}!\n"
            f"📈 Авторитет цели теперь составляет: <b>{new_rep} ⭐</b>",
            parse_mode="HTML"
        )

    # -----------------------------------------------------
    # ОБРАБОТКА РОЛЕВЫХ (RP) КОМАНД С АНИМАЦИЯМИ
    # -----------------------------------------------------
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
        except Exception as e:
            # Запасной текстовый вариант на случай падения API гифок
            await m.answer(
                f"{RP_MAP[txt]['emoji']} <b>{m.from_user.first_name}</b> "
                f"{RP_MAP[txt]['text']} <b>{target.first_name}</b>! (<i>Ошибка анимации</i>)",
                parse_mode="HTML"
            )
            return

    # -----------------------------------------------------
    # БЛОК МОДЕРАЦИИ (Проверка прав доступа)
    # -----------------------------------------------------
    is_mod = u_sender["status"] in ["moderator", "admin", "owner"] or uid == OWNER_ID
    if not is_mod:
        return

    try:
        # --- ВАРН (Предупреждение) ---
        if txt == "варн":
            new_warns = t_u["warns"] + 1
            if new_warns >= 3:
                await bot.ban_chat_member(m.chat.id, target.id)
                await db_manager.update_user(target.id, "warns", 0)
                return await m.answer(f"❌ <b>Наказание:</b> {target.mention_html()} набрал [3/3] варнов и отправляется в бан!", parse_mode="HTML")
            
            await db_manager.update_user(target.id, "warns", new_warns)
            return await m.answer(f"⚠️ <b>Внимание!</b> {target.mention_html()} получает предупреждение от модератора. [<b>{new_warns}/3</b>]", parse_mode="HTML")

        # --- МУТ IRIS-STYLE (Умное чтение времени) ---
        if txt.startswith("мут"):
            # Дефолт на 15 минут, если время не указано
            duration = timedelta(minutes=15)
            parts = txt.split()
            
            if len(parts) >= 3:
                try:
                    val = int(parts[1])
                    unit = parts[2]
                    if "м" in unit: duration = timedelta(minutes=val)
                    elif "ч" in unit: duration = timedelta(hours=val)
                    elif "д" in unit: duration = timedelta(days=val)
                except ValueError:
                    pass

            await bot.restrict_chat_member(
                m.chat.id,
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=duration
            )
            return await m.answer(f"🔇 <b>Режим тишины:</b> {target.mention_html()} лишен права голоса на <b>{duration.total_seconds()//60:.0f} мин.</b>", parse_mode="HTML")

        # --- РАЗМУТ ---
        if txt == "размут":
            await bot.restrict_chat_member(
                m.chat.id,
                target.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_manage_topics=True
                )
            )
            return await m.answer(f"🔊 <b>Снятие санкций:</b> {target.mention_html()} снова может общаться в чате.", parse_mode="HTML")

        # --- КИК ---
        if txt == "кик":
            await bot.ban_chat_member(m.chat.id, target.id)
            await bot.unban_chat_member(m.chat.id, target.id)
            return await m.answer(f"👞 <b>Исключение:</b> Пользователь {target.mention_html()} был кикнут из беседы.", parse_mode="HTML")

        # --- БАН ---
        if txt == "бан":
            await bot.ban_chat_member(m.chat.id, target.id)
            return await m.answer(f"🚷 <b>Черный список:</b> {target.mention_html()} заблокирован в этой группе без права на возврат.", parse_mode="HTML")

        # --- НАЗНАЧЕНИЕ РАНГОВ (Только Овнер/Создатель) ---
        if uid == OWNER_ID:
            if txt == "+админ":
                await db_manager.update_user(target.id, "status", "admin")
                return await m.answer(f"👑 {target.mention_html()} повышен до уровня <b>Администратора бота</b>!", parse_mode="HTML")
            
            if txt == "-админ" or txt == "-модер":
                await db_manager.update_user(target.id, "status", "user")
                return await m.answer(f"👤 Пользователь {target.mention_html()} лишен всех модераторских привилегий.", parse_mode="HTML")
            
            if txt == "+модер":
                await db_manager.update_user(target.id, "status", "moderator")
                return await m.answer(f"🛡 {target.mention_html()} теперь локальный <b>Модератор чата</b>.", parse_mode="HTML")

    except Exception as e:
        return await m.reply(f"❌ <b>Критическая ошибка выполнения:</b> Проверьте, есть ли у бота права администратора в чате!\n<code>{e}</code>", parse_mode="HTML")

# =========================================================
# ПРИВЕТСТВИЕ НОВЫХ УЧАСТНИКОВ
# =========================================================

@dp.message(F.new_chat_members)
async def welcome_bot(m: types.Message):
    for mem in m.new_chat_members:
        if mem.is_bot:
            continue
        # Регистрируем новичка
        await db_manager.get_user(mem.id, mem.full_name)
        
        await m.answer(
            f"🌸 <b>Добро пожаловать в нашу обитель, {mem.mention_html()}!</b>\n"
            f"Я твой верный бот-хранитель. Здесь ты можешь растить щечки, общаться и заводить браки.\n\n"
            f"🧁 Начни свой путь прямо сейчас, напиши: <code>тортик</code> в чат!",
            parse_mode="HTML"
        )

# =========================================================
# CORE RUNNERS
# =========================================================

async def main():
    keep_alive()

    # Запускаем SQLite
    await db_manager.init_db()

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    
    # Резервный таймер для отправки копии базы в ТГ каждые 6 часов
    async def periodic_backup():
        while True:
            await asyncio.sleep(21600)
            await db_manager.backup_db_file(bot)

    asyncio.create_task(periodic_backup())

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL FAULT: {e}")