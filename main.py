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
    return "Bot is Running Successfully!"

def run_web():
    # Render অটোমেটিক পোর্ট সেট করে দেয়, না থাকলে ৮০৮০ ব্যবহার করবে
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

# ডিফল্ট সেটিংস সেটআপ
def init_db():
    if not settings_col.find_one({"id": 1}):
        settings_col.insert_one({
            "id": 1,
            "target_chat": 0,
            "mins": 1,
            "count": 5,
            "is_forwarding": False
        })

init_db()
app = Client("ForwarderBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফরওয়ার্ডিং লুপ কন্ট্রোল
is_loop_running = False

async def forward_worker(client):
    global is_loop_running
    is_loop_running = True
    print("🚀 ফরওয়ার্ডিং লুপ চালু হয়েছে...")
    
    while True:
        conf = settings_col.find_one({"id": 1})
        
        # যদি ইউজার ফরওয়ার্ডিং বন্ধ করে দেয়
        if not conf["is_forwarding"]:
            print("🛑 ফরওয়ার্ডিং বন্ধ করা হয়েছে।")
            is_loop_running = False
            break
        
        # কিউ থেকে সিরিয়াল অনুযায়ী (পুরাতন আগে) ফাইল নেওয়া
        files = list(queue_col.find().sort("msg_id", 1).limit(conf["count"]))
        
        if not files:
            # কিউ খালি থাকলে নতুন ফাইলের জন্য ৩০ সেকেন্ড অপেক্ষা
            await asyncio.sleep(30)
            continue

        for f in files:
            try:
                # মেসেজ ফরওয়ার্ড করা
                await client.forward_messages(
                    chat_id=conf["target_chat"],
                    from_chat_id=FILE_CHANNEL_ID,
                    message_ids=f["msg_id"]
                )
                # সফল হলে কিউ থেকে ডিলিট
                queue_col.delete_one({"_id": f["_id"]})
                await asyncio.sleep(2) # ২ সেকেন্ড বিরতি
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error: {e}")
        
        # ইউজার সেট করা সময় বিরতি
        await asyncio.sleep(conf["mins"] * 60)

# --- অটো সেভ হ্যান্ডলার ---
@app.on_message(filters.chat(FILE_CHANNEL_ID))
async def auto_save(client, message):
    if not queue_col.find_one({"msg_id": message.id}):
        queue_col.insert_one({"msg_id": message.id})

# --- কমান্ডসমূহ ---

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    await message.reply_text(
        "👋 **বট অনলাইনে আছে!**\n\n"
        f"📁 সোর্স চ্যানেল: `{FILE_CHANNEL_ID}`\n"
        "আপনার সোর্স চ্যানেলে পোস্ট করলেই কিউতে সেভ হবে।\n\n"
        "⚙️ **কমান্ড:**\n"
        "🔹 `/setchannel -100xxx` - টার্গেট আইডি\n"
        "🔹 `/setmini 1` - সময় বিরতি\n"
        "🔹 `/setfrw 5` - ফরওয়ার্ড সংখ্যা\n"
        "🔹 `/forward` - শুরু করুন\n"
        "🔹 `/stop` - বন্ধ করুন\n"
        "🔹 `/stats` - রিপোর্ট দেখুন"
    )

@app.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel(client, message):
    if len(message.command) < 2: return await message.reply("চ্যানেল আইডি দিন।")
    target_id = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"target_chat": target_id}})
    await message.reply(f"✅ টার্গেট চ্যানেল সেট: `{target_id}`")

@app.on_message(filters.command("setmini") & filters.user(OWNER_ID))
async def set_mini(client, message):
    mins = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"mins": mins}})
    await message.reply(f"⏳ সময় বিরতি: `{mins}` মিনিট।")

@app.on_message(filters.command("setfrw") & filters.user(OWNER_ID))
async def set_frw(client, message):
    count = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"count": count}})
    await message.reply(f"📤 ব্যাচ প্রতি ফাইল: `{count}`টি।")

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message):
    conf = settings_col.find_one({"id": 1})
    q_count = queue_col.count_documents({})
    status = "চলছে ✅" if conf["is_forwarding"] else "বন্ধ ❌"
    
    msg = (f"📊 **বট রিপোর্ট**\n\n"
           f"📂 কিউতে আছে: `{q_count}`টি\n"
           f"🎯 টার্গেট আইডি: `{conf['target_chat']}`\n"
           f"⏱ সময়: `{conf['mins']}` মিনিট\n"
           f"📦 পরিমাণ: `{conf['count']}`টি\n"
           f"⚡ অবস্থা: {status}")
    await message.reply(msg)

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def forward_start(client, message):
    conf = settings_col.find_one({"id": 1})
    if conf["target_chat"] == 0:
        return await message.reply("⚠️ আগে টার্গেট চ্যানেল আইডি সেট করুন!")
    
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": True}})
    await message.reply("🚀 ফরওয়ার্ডিং শুরু হয়েছে।")
    if not is_loop_running:
        asyncio.create_task(forward_worker(client))

@app.on_message(filters.command("stop") & filters.user(OWNER_ID))
async def forward_stop(client, message):
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": False}})
    await message.reply("🛑 ফরওয়ার্ডিং বন্ধ করা হয়েছে।")

# --- বট স্টার্ট ---
if __name__ == "__main__":
    # Flask ওয়েব সার্ভার আলাদা থ্রেডে চালু
    threading.Thread(target=run_web, daemon=True).start()
    print("Web Server Started...")
    
    # বট চালু
    app.run()
