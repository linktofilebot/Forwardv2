import os
import sys
import subprocess
import asyncio
import logging
import re
import time
from threading import Thread
from datetime import datetime

# ==================[ ১. লাইব্রেরি অটো-ইনস্টলার ]==================
def install_requirements():
    requirements = ["pyrogram", "tgcrypto", "motor", "dnspython", "flask"]
    for package in requirements:
        try:
            __import__(package if package != "dnspython" else "dns")
        except ImportError:
            print(f"📦 Installing {package}... Please wait.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()

from pyrogram import Client, filters, errors
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask

# ==================[ ২. কনফিগারেশন সেটিংস ]==================
# নিচের তথ্যগুলো অবশ্যই সঠিক হতে হবে
API_ID = 29904834               
API_HASH = "8b4fd9ef578af114502feeafa2d31938"         
BOT_TOKEN = "8061645932:AAH1ZldPHnxDADXKXjpUFJOrDsEXEYA5I8M"       
ADMIN_ID = 7525127704           
MONGO_URL = "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0" 

# ==================[ ৩. ডাটাবেস ও লগিং সেটআপ ]==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmartForwarder")

try:
    db_client = AsyncIOMotorClient(MONGO_URL)
    db = db_client["SmartForwarderDBV2"]
    settings_col = db["settings"]
    queue_col = db["posts"]
    logger.info("✅ MongoDB Connected Successfully!")
except Exception as e:
    logger.error(f"❌ MongoDB Connection Error: {e}")
    sys.exit(1)

# ==================[ ৪. ওয়েব সার্ভার (Render Port Fix) ]==================
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return f"Bot is running...<br>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# ==================[ ৫. বট ক্লায়েন্ট ইনিশিয়ালাইজ ]==================
app = Client(
    "SmartForwarderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==================[ ৬. কোর হেল্পার ফাংশনস ]==================
async def get_config():
    conf = await settings_col.find_one({"_id": "settings"})
    if not conf:
        conf = {
            "_id": "settings", 
            "sources": [], 
            "destinations": [], 
            "limit": 1, 
            "next_serial": None
        }
        await settings_col.insert_one(conf)
    return conf

def extract_serial(message):
    """ক্যাপশন বা টেক্সটের শুরু থেকে সিরিয়াল নম্বর বের করে"""
    text = message.caption or message.text
    if text:
        match = re.search(r'^\s*(\d+)', text.strip())
        if match:
            return int(match.group(1))
    return None

# ==================[ ৭. অ্যাডমিন কমান্ড হ্যান্ডলার ]==================
@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start_handler(client, message):
    text = (
        "👋 **স্বাগতম! আমি আপনার অটো সিরিয়াল ফরওয়ার্ডার বট।**\n\n"
        "🛠 **কমান্ড লিস্ট:**\n"
        "1️⃣ `/add_source -100xxx` : সোর্স চ্যানেল আইডি সেট করুন।\n"
        "2️⃣ `/add_dest -100xxx` : মেইন চ্যানেল আইডি সেট করুন।\n"
        "3️⃣ `/limit 5` : প্রতি ঘণ্টায় পোস্টের সংখ্যা সেট করুন।\n"
        "4️⃣ `/set_serial 10` : পরবর্তী সিরিয়াল কত হবে তা ঠিক করুন।\n"
        "5️⃣ `/status` : বটের বর্তমান অবস্থা দেখুন।\n"
        "6️⃣ `/reset` : সম্পূর্ণ কিউ বা জমা ফাইল ডিলিট করুন।\n\n"
        "📌 **কিভাবে কাজ করে?**\n"
        "সোর্স চ্যানেলে ফাইল পোস্ট করার সময় ক্যাপশনের শুরুতে ১, ২ বা ৩ লিখুন। বট সেটি সিরিয়াল অনুযায়ী ফরওয়ার্ড করবে।"
    )
    await message.reply_text(text)

@app.on_message(filters.command("add_source") & filters.user(ADMIN_ID))
async def add_source(client, message):
    try:
        cid = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$addToSet": {"sources": cid}}, upsert=True)
        await message.reply_text(f"✅ সোর্স চ্যানেল `{cid}` অ্যাড করা হয়েছে।")
    except:
        await message.reply_text("❌ আইডি ভুল! সঠিক ফরম্যাট: `/add_source -100123456789`")

@app.on_message(filters.command("add_dest") & filters.user(ADMIN_ID))
async def add_dest(client, message):
    try:
        cid = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$addToSet": {"destinations": cid}}, upsert=True)
        await message.reply_text(f"✅ ডেসটিনেশন চ্যানেল `{cid}` অ্যাড করা হয়েছে।")
    except:
        await message.reply_text("❌ আইডি ভুল! সঠিক ফরম্যাট: `/add_dest -100123456789`")

@app.on_message(filters.command("limit") & filters.user(ADMIN_ID))
async def set_limit(client, message):
    try:
        val = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$set": {"limit": val}})
        await message.reply_text(f"⚙️ প্রতি ঘণ্টায় `{val}` টি পোস্ট ফরওয়ার্ড করা হবে।")
    except:
        await message.reply_text("❌ সঠিক সংখ্যা দিন। উদাহরণ: `/limit 5`")

@app.on_message(filters.command("set_serial") & filters.user(ADMIN_ID))
async def set_serial(client, message):
    try:
        val = int(message.command[1])
        await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": val}})
        await message.reply_text(f"🔢 পরবর্তী সিরিয়াল `{val}` সেট করা হয়েছে।")
    except:
        await message.reply_text("❌ ব্যবহার: `/set_serial 10`")

@app.on_message(filters.command("status") & filters.user(ADMIN_ID))
async def get_status(client, message):
    s = await get_config()
    q_count = await queue_col.count_documents({})
    text = (
        f"📊 **বট স্ট্যাটাস রিপোর্ট:**\n\n"
        f"🔹 পরবর্তী সিরিয়াল: `{s.get('next_serial') or 'N/A'}`\n"
        f"🔹 কিউতে জমা ফাইল: `{q_count}` টি\n"
        f"🔹 বর্তমান স্পিড: `{s['limit']}` টি/ঘণ্টা\n"
        f"🔹 সোর্স সংখ্যা: `{len(s['sources'])}` টি\n"
        f"🔹 ডেসটিনেশন সংখ্যা: `{len(s['destinations'])}` টি"
    )
    await message.reply_text(text)

@app.on_message(filters.command("reset") & filters.user(ADMIN_ID))
async def reset_queue(client, message):
    await queue_col.delete_many({})
    await message.reply_text("🗑 কিউ খালি করা হয়েছে। সব জমা ফাইল মুছে গেছে।")

# ==================[ ৮. ফাইল সংগ্রাহক (Collector Logic) ]==================
@app.on_message(filters.chat)
async def collector_logic(client, message):
    config = await get_config()
    
    # সোর্স চ্যানেল থেকে মেসেজ আসলে সেটি সেভ করবে
    if message.chat.id in config["sources"]:
        serial = extract_serial(message)
        if serial is not None:
            await queue_col.update_one(
                {"serial": serial},
                {"$set": {
                    "from_id": message.chat.id,
                    "msg_id": message.id,
                    "serial": serial,
                    "timestamp": time.time()
                }},
                upsert=True
            )
            logger.info(f"📥 Saved: Serial {serial} from {message.chat.id}")
            
            # প্রথমবার মেসেজ আসলে অটো পরবর্তী সিরিয়াল সেট করা
            if config.get("next_serial") is None:
                await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": serial}})
        else:
            logger.warning(f"⚠️ No serial found in message ID {message.id}")

# ==================[ ৯. ব্যাকগ্রাউন্ড ওয়ার্কার (Forwarder Logic) ]==================
async def forwarder_worker():
    logger.info("🚀 Forwarder Worker Started!")
    while True:
        try:
            config = await get_config()
            target_serial = config.get("next_serial")
            
            # যদি পরবর্তী সিরিয়াল সেট না থাকে, ডাটাবেসের সর্বনিম্ন সিরিয়াল নিবে
            if target_serial is None:
                first_item = await queue_col.find_one({}, sort=[("serial", 1)])
                if first_item:
                    target_serial = first_item["serial"]
                    await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": target_serial}})

            # সিরিয়াল অনুযায়ী ফাইল খোঁজা
            post = await queue_col.find_one({"serial": target_serial})
            
            if post and config["destinations"]:
                # মূল মেসেজটি গেট করা (বাটন ও ক্যাপশন সহ কপি করার জন্য)
                try:
                    original_msg = await app.get_messages(post["from_id"], post["msg_id"])
                    
                    if original_msg.empty:
                        logger.error(f"❌ Msg {post['msg_id']} not found or deleted. Skipping...")
                        await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": target_serial + 1}})
                        continue

                    # ক্যালকুলেট ডিলে (Limit অনুযায়ী)
                    interval = 3600 / max(config["limit"], 1)
                    
                    # প্রতিটি ডেসটিনেশন চ্যানেলে পাঠানো
                    for dest_id in config["destinations"]:
                        try:
                            # কপি মেসেজ বাটন ও ক্যাপশন সব নিয়ে নেয়
                            await app.copy_message(
                                chat_id=dest_id,
                                from_chat_id=post["from_id"],
                                message_id=post["msg_id"],
                                reply_markup=original_msg.reply_markup
                            )
                        except errors.FloodWait as fw:
                            await asyncio.sleep(fw.value)
                        except Exception as e:
                            logger.error(f"❌ Error sending to {dest_id}: {e}")

                    # সফলভাবে পাঠানো হলে ডাটাবেস থেকে রিমুভ ও সিরিয়াল আপডেট
                    await queue_col.delete_one({"_id": post["_id"]})
                    await settings_col.update_one({"_id": "settings"}, {"$set": {"next_serial": target_serial + 1}})
                    
                    logger.info(f"✅ Serial {target_serial} Sent. Sleeping {interval}s")
                    await asyncio.sleep(interval)

                except Exception as e:
                    logger.error(f"❌ Worker Logic Error: {e}")
                    await asyncio.sleep(10)
            else:
                # যদি সিরিয়াল অনুযায়ী ফাইল না থাকে, ১৫ সেকেন্ড ওয়েট করবে
                await asyncio.sleep(15)
        
        except Exception as e:
            logger.error(f"❌ Fatal Worker Error: {e}")
            await asyncio.sleep(30)

# ==================[ ১০. রান ও এক্সিকিউশন ]==================
if __name__ == "__main__":
    # ১. ওয়েব সার্ভার থ্রেড চালু করা (Render এর জন্য)
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # ২. ইভেন্ট লুপে ওয়ার্কার অ্যাড করা
    loop = asyncio.get_event_loop()
    loop.create_task(forwarder_worker())
    
    # ৩. বট রান করা
    logger.info("🤖 Bot is Starting...")
    app.run()
