import os
import re
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
import aiosqlite

BOT_TOKEN = os.getenv("SECURITY_BOT_TOKEN")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER", "8581086019"))
GROUPS_LOGS = int(os.getenv("GROUPS_LOGS", "-1001234567890"))
DB_PATH = os.getenv("DB_PATH", "cyberpup_security.db")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                chat_id INTEGER,
                message_count INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                violations INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.commit()

async def get_user_stats(user_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT message_count, reputation, violations FROM users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        if not row:
            await db.execute("INSERT INTO users (user_id, chat_id) VALUES (?, ?)", (user_id, chat_id))
            await db.commit()
            return 0, 0, 0
        return row

async def update_user(user_id: int, chat_id: int, msg_inc: int = 0, rep_change: int = 0, viol_inc: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, chat_id, message_count, reputation, violations)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                message_count = message_count + EXCLUDED.message_count,
                reputation = reputation + EXCLUDED.reputation,
                violations = violations + EXCLUDED.violations
        """, (user_id, chat_id, msg_inc, rep_change, viol_inc))
        await db.commit()

CJK_PATTERN = re.compile(r'[\u4e00-\u9fff]')
INVISIBLE_CHARS = ['\u115f', '\u1160', '\u3164', '\uffa0']

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def security_pipeline(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    chat_member = await bot.get_chat_member(chat_id, user_id)
    if user_id == BOT_OWNER_ID or chat_member.status in ["administrator", "creator"]:
        return

    msg_count, rep, violations = await get_user_stats(user_id, chat_id)
    text = message.text or message.caption or ""

    if CJK_PATTERN.search(text):
        await message.delete()
        await update_user(user_id, chat_id, rep_change=-5, viol_inc=1)
        await bot.send_message(GROUPS_LOGS, f"🚨 **CJK Spam Detected**\nUser: {user_id}\nGroup: {chat_id}")
        return

    if rep < 50 and any(char in text for char in INVISIBLE_CHARS):
        await message.delete()
        await update_user(user_id, chat_id, rep_change=-10, viol_inc=1)
        await bot.send_message(GROUPS_LOGS, f"🚨 **Invisible Spacing Violation**\nUser: {user_id}")
        return

    if violations >= 100 and rep < 100:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.send_message(GROUPS_LOGS, f"⛔ **Auto-Banned User**: {user_id} (Violations: {violations}, Rep: {rep})")
        return

    await update_user(user_id, chat_id, msg_inc=1, rep_change=1)

@dp.message(Command("info", "me", "whoami"))
async def user_info(message: types.Message):
    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    msg_count, rep, viol = await get_user_stats(target_user.id, message.chat.id)
    await message.reply(
        f"🐾 **Member Profile**: {target_user.mention_html()}\n"
        f"📊 **Messages**: {msg_count}\n"
        f"⭐ **Reputation**: {rep}\n"
        f"⚠️ **Violations**: {viol}",
        parse_mode=ParseMode.HTML
    )

async def main():
    await init_db()
    print("CyberPUP Security Bot initialized.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
