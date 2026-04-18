# --- УЛУЧШЕННАЯ МОДЕРАЦИЯ ---

# Функция проверки: является ли пользователь админом
async def is_admin(m: types.Message):
    member = await m.chat.get_member(m.from_user.id)
    return member.status in ["administrator", "creator"]

@dp.message(F.text.casefold().startswith("мут"))
async def mute_handler(m: types.Message):
    if not await is_admin(m): 
        return await m.reply("У тебя нет прав отдавать такие приказы! 😤")
    
    if not m.reply_to_message:
        return await m.reply("Нужно ответить на сообщение того, кого хочешь отправить в угол!")

    # Мутим на 10 минут по умолчанию
    try:
        await m.chat.restrict(
            m.reply_to_message.from_user.id, 
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=10)
        )
        await m.answer(f"🤫 {m.reply_to_message.from_user.first_name} отправлен(а) в уголок тишины. Подумай над своим поведением!")
    except Exception:
        await m.answer("Ой, у меня не хватает прав, чтобы его замутить. Сделай меня админом!")

@dp.message(F.text.casefold().startswith("размут"))
async def unmute_handler(m: types.Message):
    if not await is_admin(m): return
    if not m.reply_to_message: return

    await m.chat.restrict(
        m.reply_to_message.from_user.id,
        permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=True, can_invite_users=True, can_pin_messages=True, can_manage_topics=True)
    )
    await m.answer(f"✨ Ладно, {m.reply_to_message.from_user.first_name}, выходи из угла. Больше не хулигань!")

@dp.message(F.text.casefold().startswith("варн"))
async def warn_handler(m: types.Message):
    if not await is_admin(m): return
    if not m.reply_to_message: return

    target_id = m.reply_to_message.from_user.id
    check_user(target_id, m.reply_to_message.from_user.first_name)
    
    user_data[target_id]["warns"] += 1
    count = user_data[target_id]["warns"]

    if count >= 3:
        await m.chat.ban(target_id)
        user_data[target_id]["warns"] = 0 # Сброс после бана
        await m.answer(f"🚫 {m.reply_to_message.from_user.first_name} набрал(а) 3/3 предупреждений и покидает нас. Прощай!")
    else:
        await m.answer(f"⚠️ {m.reply_to_message.from_user.first_name}, это предупреждение! ({count}/3). Веди себя мило!")

@dp.message(F.text.casefold().startswith("бан"))
async def ban_handler(m: types.Message):
    if not await is_admin(m): return
    if not m.reply_to_message: return

    await m.chat.ban(m.reply_to_message.from_user.id)
    await m.answer(f"📦 Каоруко собрала чемоданы для {m.reply_to_message.from_user.first_name}. Счастливого пути!")