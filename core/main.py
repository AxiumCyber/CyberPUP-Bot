import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType, ParseMode
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("CORE_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://claw-mongo:27017")
SUDOERS = [int(x) for x in os.getenv("SUDOERS", "8581086019").split(",")]

app = Client("cyberpup_core", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.cyberpup_core

async def send_log(chat_id: int, log_text: str):
    indiv_doc = await db.log_channels.find_one({"_id": chat_id})
    indiv_log = indiv_doc.get("log_channel_id") if indiv_doc else None

    gen_doc = await db.settings.find_one({"_id": "general_logs"})
    gen_log = gen_doc.get("log_channel_id") if gen_doc else None

    destinations = set(filter(None, [indiv_log, gen_log]))
    for log_channel in destinations:
        try:
            await app.send_message(log_channel, log_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Log dispatch error to {log_channel}: {e}")

@app.on_message(filters.command("ban") & filters.group)
async def ban_user(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply("Reply to a user's message to execute a ban.")
    
    target = message.reply_to_message.from_user
    await client.ban_chat_member(message.chat.id, target.id)
    await message.reply(f"🚫 Banned {target.mention}")
    
    await send_log(
        message.chat.id,
        f"<b>Ban Action</b>\n<b>Group:</b> {message.chat.title}\n<b>Target:</b> {target.mention}\n<b>Admin:</b> {message.from_user.mention}"
    )

@app.on_message(filters.command("setlog"))
async def set_log_channel(client: Client, message: Message):
    user_id = message.from_user.id
    
    if message.chat.type == ChatType.PRIVATE:
        if user_id not in SUDOERS:
            return
        if len(message.command) < 2:
            return await message.reply("Usage in DM: `/setlog -100xxxx` to specify GENERAL aggregate channel.")
        
        target_log = int(message.command[1])
        await db.settings.update_one({"_id": "general_logs"}, {"$set": {"log_channel_id": target_log}}, upsert=True)
        await message.reply(f"✅ GENERAL log channel mapped to `{target_log}`.")

    elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if len(message.command) < 2:
            return await message.reply("Usage in group: `/setlog -100xxxx` to specify INDIVIDUAL group channel.")
        
        target_log = int(message.command[1])
        await db.log_channels.update_one({"_id": message.chat.id}, {"$set": {"log_channel_id": target_log}}, upsert=True)
        await message.reply(f"✅ INDIVIDUAL group log channel mapped to `{target_log}`.")

if __name__ == "__main__":
    print("CyberPUP Core Bot initialized.")
    app.run()
