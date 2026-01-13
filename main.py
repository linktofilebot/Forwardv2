import os
import sys
import asyncio
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pymongo import MongoClient

# --- Flask সার্ভার (Render-এ পোর্ট এরর এড়াতে) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running with Button Support!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- অটো লাইব্রেরি ইনস্টলার ---
def install_libraries():
    try:
        import pyrogram
        import pymongo
        import tgcrypto
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto", "pymongo", "dnspython", "flask"])

install_libraries()

# ==================== আপনার কনফিগারেশন ====================
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8061645932:AAH1ZldPHnxDADXKXjpUFJOrDsEXEYA5I8M"
OWNER_ID = 7525127704
MONGO_URI = "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003657918890
# =========================================================

# --- ডেটাবেস কানেকশন ---
db_client = MongoClient(MONGO_URI)
db = db_client["AutoForwarderDB"]
queue_col = db["queue"]
settings_col = db["settings"]

def init_db():
    if not settings_col.find_one({"id": 1}):
        settings_col.insert_one({"id": 1, "target_chat": 0, "mins": 1, "count": 5, "is_forwarding": False})

init_db()
app = Client("ForwarderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

is_loop_running = False

async def forward_worker(client):
    global is_loop_running
    is_loop_running = True
    print("🚀 বাটনসহ ফরওয়ার্ডিং লুপ চালু হয়েছে...")
    
    while True:
        conf = settings_col.find_one({"id": 1})
        if not conf["is_forwarding"]:
            is_loop_running = False
            break
        
        files = list(queue_col.find().sort("msg_id", 1).limit(conf["count"]))
        if not files:
            await asyncio.sleep(30)
            continue

        for f in files:
            try:
                # বাটনসহ পাঠানোর জন্য এখানে copy_message ব্যবহার করা হয়েছে
                await client.copy_message(
                    chat_id=conf["target_chat"],
                    from_chat_id=FILE_CHANNEL_ID,
                    message_id=f["msg_id"]
                )
                queue_col.delete_one({"_id": f["_id"]})
                await asyncio.sleep(2) 
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error copying msg {f['msg_id']}: {e}")
        
        await asyncio.sleep(conf["mins"] * 60)

# --- অটো সেভ ---
@app.on_message(filters.chat(FILE_CHANNEL_ID))
async def auto_save(client, message):
    if not queue_col.find_one({"msg_id": message.id}):
        queue_col.insert_one({"msg_id": message.id})

# --- কমান্ডসমূহ ---
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    await message.reply_text("👋 **বাটন সাপোর্ট অন আছে!**\n/forward দিলে বাটনসহ কপি হবে।")

@app.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel(client, message):
    if len(message.command) < 2: return
    tid = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"target_chat": tid}})
    await message.reply(f"🎯 টার্গেট সেট: {tid}")

@app.on_message(filters.command("setmini") & filters.user(OWNER_ID))
async def set_mini(client, message):
    mins = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"mins": mins}})
    await message.reply(f"⏳ বিরতি: {mins} মিনিট")

@app.on_message(filters.command("setfrw") & filters.user(OWNER_ID))
async def set_frw(client, message):
    count = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"count": count}})
    await message.reply(f"📦 ফাইল সংখ্যা: {count}")

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message):
    conf = settings_col.find_one({"id": 1})
    q = queue_col.count_documents({})
    status = "চলছে ✅" if conf["is_forwarding"] else "বন্ধ ❌"
    await message.reply(f"📊 রিপোর্ট:\nকিউতে আছে: {q} টি\nঅবস্থা: {status}")

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def forward_start(client, message):
    conf = settings_col.find_one({"id": 1})
    if conf["target_chat"] == 0: return await message.reply("⚠️ টার্গেট আইডি সেট নেই!")
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": True}})
    await message.reply("🚀 বাটনসহ ফরওয়ার্ডিং শুরু হলো।")
    if not is_loop_running: asyncio.create_task(forward_worker(client))

@app.on_message(filters.command("stop") & filters.user(OWNER_ID))
async def forward_stop(client, message):
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": False}})
    await message.reply("🛑 বন্ধ করা হয়েছে।")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    app.run()
