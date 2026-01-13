import os
import sys
import asyncio
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pymongo import MongoClient

# --- Flask Server (Render-এর জন্য) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running! Check /stats for progress."

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- লাইব্রেরি ইনস্টলার ---
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

# গ্লোবাল ভেরিয়েবল ফর স্ট্যাটস
stats = {
    "sent_this_session": 0,
    "new_added_during_session": 0
}

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

is_loop_running = False

async def forward_worker(client):
    global is_loop_running
    is_loop_running = True
    
    while True:
        conf = settings_col.find_one({"id": 1})
        if not conf["is_forwarding"]:
            is_loop_running = False
            break
        
        # কিউ থেকে ফাইল নেওয়া
        files = list(queue_col.find().sort("msg_id", 1).limit(conf["count"]))
        
        if not files:
            # কিউ খালি থাকলে ৩০ সেকেন্ড পর চেক করবে
            await asyncio.sleep(30)
            continue

        for f in files:
            try:
                # copy_message বাটন এবং ক্যাপশন সহ কপি করার সেরা উপায়
                await client.copy_message(
                    chat_id=conf["target_chat"],
                    from_chat_id=FILE_CHANNEL_ID,
                    message_id=f["msg_id"]
                )
                queue_col.delete_one({"_id": f["_id"]})
                stats["sent_this_session"] += 1
                await asyncio.sleep(2) # FloodWait এড়াতে গ্যাপ
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error copying msg {f['msg_id']}: {e}")
        
        # সেটিং অনুযায়ী বিরতি
        await asyncio.sleep(conf["mins"] * 60)

# --- অটো সেভ এবং নতুন ফাইল ট্র্যাকিং ---
@app.on_message(filters.chat(FILE_CHANNEL_ID))
async def auto_save(client, message):
    if not queue_col.find_one({"msg_id": message.id}):
        queue_col.insert_one({"msg_id": message.id})
        # যদি ফরওয়ার্ডিং চলাকালীন নতুন ফাইল আসে
        conf = settings_col.find_one({"id": 1})
        if conf["is_forwarding"]:
            stats["new_added_during_session"] += 1

# --- কমান্ডসমূহ ---
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    await message.reply_text(
        "👋 **বাটন সাপোর্ট এনাবেল্ড অটো ফরওয়ার্ডার!**\n\n"
        "কমান্ডসমূহ:\n"
        "🔹 /setchannel [ID] - টার্গেট চ্যানেল সেট\n"
        "🔹 /setmini [মিনিট] - সময় বিরতি\n"
        "🔹 /setfrw [সংখ্যা] - প্রতিবার কতটি ফাইল\n"
        "🔹 /forward - ফরওয়ার্ড শুরু\n"
        "🔹 /stop - ফরওয়ার্ড বন্ধ\n"
        "🔹 /stats - বিস্তারিত রিপোর্ট"
    )

@app.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel(client, message):
    if len(message.command) < 2: return
    try:
        tid = int(message.command[1])
        settings_col.update_one({"id": 1}, {"$set": {"target_chat": tid}})
        await message.reply(f"🎯 **টার্গেট সেট করা হয়েছে:** `{tid}`")
    except:
        await message.reply("❌ সঠিক আইডি দিন।")

@app.on_message(filters.command("setmini") & filters.user(OWNER_ID))
async def set_mini(client, message):
    if len(message.command) < 2: return
    mins = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"mins": mins}})
    await message.reply(f"⏳ **বিরতি:** {mins} মিনিট সেট করা হয়েছে।")

@app.on_message(filters.command("setfrw") & filters.user(OWNER_ID))
async def set_frw(client, message):
    if len(message.command) < 2: return
    count = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"count": count}})
    await message.reply(f"📦 **ব্যাচ ফাইল সংখ্যা:** {count} টি।")

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def get_stats(client, message):
    conf = settings_col.find_one({"id": 1})
    remaining = queue_col.count_documents({})
    status = "চলছে ✅" if conf["is_forwarding"] else "বন্ধ ❌"
    
    text = (
        "📊 **লাইভ ফরওয়ার্ডিং রিপোর্ট**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"✅ **অবস্থা:** {status}\n"
        f"📤 **সেশনে পাঠানো হয়েছে:** {stats['sent_this_session']} টি\n"
        f"⏳ **কিউতে বাকি আছে:** {remaining} টি\n"
        f"➕ **সেশন চলাকালীন নতুন যোগ:** {stats['new_added_during_session']} টি\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ **টার্গেট:** `{conf['target_chat']}`\n"
        f"⚙️ **কনফিগ:** {conf['count']}টি ফাইল / {conf['mins']} মিনিট পর পর।"
    )
    await message.reply(text)

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def forward_start(client, message):
    conf = settings_col.find_one({"id": 1})
    if conf["target_chat"] == 0: 
        return await message.reply("⚠️ আগে `/setchannel` ব্যবহার করে টার্গেট আইডি সেট করুন।")
    
    # নতুন সেশন শুরু হলে স্ট্যাটস রিসেট
    stats["sent_this_session"] = 0
    stats["new_added_during_session"] = 0
    
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": True}})
    await message.reply("🚀 **বাটনসহ ফরওয়ার্ডিং শুরু হলো!**\nআপডেট দেখতে /stats লিখুন।")
    
    if not is_loop_running: 
        asyncio.create_task(forward_worker(client))

@app.on_message(filters.command("stop") & filters.user(OWNER_ID))
async def forward_stop(client, message):
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": False}})
    await message.reply("🛑 **ফরওয়ার্ডিং বন্ধ করা হয়েছে।**")

if __name__ == "__main__":
    # Flask সার্ভার স্টার্ট
    threading.Thread(target=run_web, daemon=True).start()
    # বট স্টার্ট
    app.run()
