import os
import sys
import asyncio
import subprocess

# --- অটো লাইব্রেরি ইনস্টলার ---
def install_libraries():
    try:
        import pyrogram
        import pymongo
        import tgcrypto
    except ImportError:
        print("প্রয়োজনীয় লাইব্রেরি ইনস্টল হচ্ছে... দয়া করে অপেক্ষা করুন।")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto", "pymongo", "dnspython"])
        print("লাইব্রেরি ইনস্টল সম্পন্ন হয়েছে।")

install_libraries()

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pymongo import MongoClient

# ==================== কনফিগারেশন (আপনার তথ্য এখানে দিন) ====================
API_ID = 29904834                     # আপনার API ID (my.telegram.org থেকে)
API_HASH = "8b4fd9ef578af114502feeafa2d31938"           # আপনার API HASH
BOT_TOKEN = "8061645932:AAH1ZldPHnxDADXKXjpUFJOrDsEXEYA5I8M"         # BotFather থেকে পাওয়া টোকেন
OWNER_ID = 7525127704                  # আপনার নিজের টেলিগ্রাম ইউজার আইডি
MONGO_URI = "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0"       # আপনার MongoDB Connection URI
FILE_CHANNEL_ID = -1003657918890     # ফাইল চ্যানেলের আইডি (যেখান থেকে অটো সেভ হবে)
# =========================================================================

# --- ডেটাবেস সেটআপ ---
db_client = MongoClient(MONGO_URI)
db = db_client["AutoForwarderDB"]
queue_col = db["queue"]
settings_col = db["settings"]

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

def get_config():
    return settings_col.find_one({"id": 1})

# --- ব্যাকগ্রাউন্ড ফরওয়ার্ডিং লকার ---
# এটি নিশ্চিত করে যে একসাথে দুটি লুপ চালু হবে না
is_loop_running = False

async def forward_worker(client):
    global is_loop_running
    is_loop_running = True
    print("ফরওয়ার্ডিং লুপ শুরু হয়েছে...")
    
    while True:
        conf = get_config()
        
        # যদি ফরওয়ার্ডিং বন্ধ করা হয়
        if not conf["is_forwarding"]:
            print("ফরওয়ার্ডিং বন্ধ করা হয়েছে।")
            is_loop_running = False
            break
        
        # কিউ থেকে সিরিয়াল অনুযায়ী (পুরাতন আগে) ফাইল নেওয়া
        files = list(queue_col.find().sort("msg_id", 1).limit(conf["count"]))
        
        if not files:
            # কিউ খালি থাকলে ৩০ সেকেন্ড পর আবার চেক করবে
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
                # সফল হলে কিউ থেকে ডিলেট
                queue_col.delete_one({"_id": f["_id"]})
                await asyncio.sleep(2) # ২ সেকেন্ড বিরতি (সেফটি)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Error for msg_id {f['msg_id']}: {e}")
        
        # বিরতি সময় (মিনিট থেকে সেকেন্ড)
        await asyncio.sleep(conf["mins"] * 60)

# --- অটো সেভ হ্যান্ডলার (চ্যানেলে পোস্ট করলেই সেভ হবে) ---
@app.on_message(filters.chat(FILE_CHANNEL_ID))
async def auto_save(client, message):
    if not queue_col.find_one({"msg_id": message.id}):
        queue_col.insert_one({"msg_id": message.id})
        # পোস্ট আসলে প্রিন্ট হবে (অপশনাল)
        print(f"নতুন ফাইল কিউতে সেভ হয়েছে: {message.id}")

# --- কমান্ড হ্যান্ডলারসমূহ ---

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    await message.reply_text(
        "👋 **বট অনলাইনে আছে!**\n\n"
        f"📁 ফাইল চ্যানেল: `{FILE_CHANNEL_ID}`\n"
        "বটটি অটো-সেভ মোডে আছে। চ্যানেলে পোস্ট করলেই কিউতে জমা হবে।\n\n"
        "⚙️ **কমান্ডসমূহ:**\n"
        "🔹 `/setchannel -100xxx` - টার্গেট চ্যানেল সেট করুন\n"
        "🔹 `/setmini 5` - কত মিনিট বিরতি হবে\n"
        "🔹 `/setfrw 10` - প্রতিবারে কত ফাইল যাবে\n"
        "🔹 `/forward` - ফরওয়ার্ড শুরু করুন\n"
        "🔹 `/stop` - ফরওয়ার্ড বন্ধ করুন\n"
        "🔹 `/stats` - বর্তমান অবস্থা দেখুন"
    )

@app.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def set_channel(client, message):
    if len(message.command) < 2:
        return await message.reply("টার্গেট চ্যানেলের আইডি দিন।")
    target_id = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"target_chat": target_id}})
    await message.reply(f"✅ টার্গেট চ্যানেল সেট হয়েছে: `{target_id}`")

@app.on_message(filters.command("setmini") & filters.user(OWNER_ID))
async def set_mini(client, message):
    if len(message.command) < 2: return
    mins = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"mins": mins}})
    await message.reply(f"⏳ বিরতি সময় সেট: `{mins}` মিনিট।")

@app.on_message(filters.command("setfrw") & filters.user(OWNER_ID))
async def set_frw(client, message):
    if len(message.command) < 2: return
    count = int(message.command[1])
    settings_col.update_one({"id": 1}, {"$set": {"count": count}})
    await message.reply(f"📤 প্রতিবারে `{count}`টি ফাইল ফরওয়ার্ড হবে।")

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message):
    conf = get_config()
    total_in_queue = queue_col.count_documents({})
    status = "চলছে ✅" if conf["is_forwarding"] else "বন্ধ ❌"
    
    msg = (f"📊 **বট স্ট্যাটাস রিপোর্ট**\n\n"
           f"📁 সোর্স চ্যানেল: `{FILE_CHANNEL_ID}`\n"
           f"🎯 টার্গেট চ্যানেল: `{conf['target_chat']}`\n"
           f"📂 কিউতে বাকি ফাইল: `{total_in_queue}`টি\n"
           f"⏱ বিরতি সময়: `{conf['mins']}` মিনিট\n"
           f"📦 ব্যাচ সাইজ: `{conf['count']}`টি\n"
           f"⚡ অবস্থা: {status}")
    await message.reply(msg)

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def start_fwd(client, message):
    conf = get_config()
    if conf["target_chat"] == 0:
        return await message.reply("⚠️ আগে টার্গেট চ্যানেল সেট করুন!")
    
    if conf["is_forwarding"]:
        return await message.reply("▶️ ফরওয়ার্ডিং ইতোমধ্যে চলছে।")
    
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": True}})
    await message.reply("🚀 ফরওয়ার্ডিং প্রসেস শুরু হয়েছে!")
    
    if not is_loop_running:
        asyncio.create_task(forward_worker(client))

@app.on_message(filters.command("stop") & filters.user(OWNER_ID))
async def stop_fwd(client, message):
    settings_col.update_one({"id": 1}, {"$set": {"is_forwarding": False}})
    await message.reply("🛑 ফরওয়ার্ডিং বন্ধ করা হয়েছে।")

print("বটটি চালু হচ্ছে...")
app.run()
