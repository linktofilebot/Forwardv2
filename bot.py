import os
import sys
import subprocess
import asyncio
import logging
import re

# ==================[ অটো লাইব্রেরি ইনস্টল সিস্টেম ]==================
def install_requirements():
    requirements = ["pyrogram", "tgcrypto", "motor", "dnspython"]
    for package in requirements:
        try:
            __import__(package if package != "dnspython" else "dns")
        except ImportError:
            print(f"Installing {package}... Please wait.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()

from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient

# ==================[ এখানে আপনার তথ্যগুলো বসান ]==================
API_ID = 1234567               # আপনার API ID (my.telegram.org থেকে)
API_HASH = "your_hash"         # আপনার API HASH (my.telegram.org থেকে)
BOT_TOKEN = "your_token"       # আপনার বোট টোকেন (@BotFather থেকে)
ADMIN_ID = 123456789           # আপনার নিজের টেলিগ্রাম আইডি (অ্যাডমিন)
MONGO_URL = "mongodb+srv://..." # আপনার MongoDB ইউআরএল (Atlas থেকে)
# =============================================================

# লগিং সেটিংস
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ডাটাবেস কানেকশন
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["SmartForwarderDB"]
settings_col = db["settings"]
queue_col = db["posts"]

app = Client("auto_serial_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- হেল্পার ফাংশন ---
async def get_config():
    conf = await settings_col.find_one({"_id": "settings"})
    if not conf:
        conf = {"_id": "settings", "sources": [], "destinations": [], "limit": 1, "next_serial": None}
        await settings_col.insert_one(conf)
    return conf

def get_serial(message):
    text = message.text or message.caption
    if text:
        match = re.search(r'^(\d+)', text.strip())
        return int(match.group(1)) if match else None
    return None

# --- কমান্ড হ্যান্ডলার ---
@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply_text(
        "🚀 **বট এখন সচল!**\n\n"
        "**সেটআপ গাইড:**\n"
        "1️⃣ `/add_source -100xxx` : ফাইল রাখার চ্যানেল আইডি\n"
        "2️⃣ `/add_dest -100xxx` : মেইন চ্যানেল আইডি (যেখানে পোস্ট যাবে)\n"
        "3️⃣ `/limit 5` : প্রতি ঘণ্টায় ৫টি ফাইল যাবে\n"
        "4️⃣ `/status` : কিউ এবং সিরিয়াল চেক করুন\n\n"
        "📌 *ফাইল আপলোড করার সময় ক্যাপশনের শুরুতে ১, ২, ৩ এভাবে নাম্বার দিন।*")

@app.on_message(filters.command("add_source") & filters.user(ADMIN_ID))
async def add_src(client, message):
    try:
        cid = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$addToSet": {"sources": cid}}, upsert=True)
        await message.reply_text(f"✅ সোর্স চ্যানেল `{cid}` যুক্ত হয়েছে।")
    except: await message.reply_text("সঠিক আইডি দিন!")

@app.on_message(filters.command("add_dest") & filters.user(ADMIN_ID))
async def add_dst(client, message):
    try:
        cid = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$addToSet": {"destinations": cid}}, upsert=True)
        await message.reply_text(f"✅ ডেসটিনেশন চ্যানেল `{cid}` যুক্ত হয়েছে।")
    except: await message.reply_text("সঠিক আইডি দিন!")

@app.on_message(filters.command("limit") & filters.user(ADMIN_ID))
async def set_limit(client, message):
    try:
        l = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$set": {"limit": l}})
        await message.reply_text(f"⚙️ লিমিট: প্রতি ঘণ্টায় {l}টি পোস্ট সেট করা হয়েছে।")
    except: await message.reply_text("সঠিক সংখ্যা দিন!")

@app.on_message(filters.command("status") & filters.user(ADMIN_ID))
async def status(client, message):
    s = await get_config()
    q = await queue_col.count_documents({})
    p = s.get("next_serial") or "অটো ডিটেক্ট..."
    await message.reply_text(f"📊 **স্ট্যাটাস:**\n- পরবর্তী সিরিয়াল: {p}\n- কিউতে আছে: {q}টি ফাইল\n- লিমিট: {s['limit']} টি/ঘণ্টা")

# --- ফাইল রিসিভার ---
@app.on_message(filters.chat)
async def collector(client, message):
    s = await get_config()
    if message.chat.id in s["sources"]:
        serial = get_serial(message)
        if serial is not None:
            await queue_col.update_one(
                {"serial": serial},
                {"$set": {"from_id": message.chat.id, "msg_id": message.id, "serial": serial}},
                upsert=True
            )
            logger.info(f"সিরিয়াল {serial} সেভ করা হয়েছে।")
            # যদি আগে কোনো সিরিয়াল সেট না থাকে, তবে এটিই প্রথম সিরিয়াল হবে
            if s.get("next_serial") is None:
                await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": serial}})

# --- অটো ফরওয়ার্ডার ওয়ার্কার ---
async def worker():
    while True:
        s = await get_config()
        ptr = s.get("next_serial")
        
        # যদি পরবর্তী কোনো সিরিয়াল সেট না থাকে, ডাটাবেসের সর্বনিম্নটি নিবে
        if ptr is None:
            first = await queue_col.find_one({}, sort=[("serial", 1)])
            if first:
                ptr = first["serial"]
                await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": ptr}})

        # সিরিয়াল অনুযায়ী ফাইল আছে কি না চেক
        task = await queue_col.find_one({"serial": ptr})
        
        if task and s["destinations"]:
            delay = 3600 / s["limit"]
            for d in s["destinations"]:
                try:
                    # copy_message বাটন এবং ক্যাপশন হুবহু কপি করে
                    await app.copy_message(chat_id=d, from_chat_id=task["from_id"], message_id=task["msg_id"])
                except Exception as e:
                    logger.error(f"Error: {e}")
            
            # পাঠানো শেষ হলে কিউ থেকে ডিলিট এবং পরের সিরিয়াল সেট
            await queue_col.delete_one({"_id": task["_id"]})
            await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": ptr + 1}})
            logger.info(f"Serial {ptr} Sent. Waiting {delay}s...")
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(15) # সিরিয়াল না পাওয়া গেলে অপেক্ষা

# --- রান বোট ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(worker())
    print(">>> বট চালু হয়েছে! টেলিগ্রামে কমান্ড দিন।")
    app.run()
