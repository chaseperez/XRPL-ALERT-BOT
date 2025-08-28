import os
import logging
import requests
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from flask import Flask
from threading import Thread

# ----------------------------
# Setup
# ----------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
APP_URL = os.getenv("APP_URL")  # Render app URL for self-ping

if not BOT_TOKEN or not CHAT_ID or not APP_URL:
    raise RuntimeError("❌ BOT_TOKEN, CHAT_ID, or APP_URL missing in environment variables!")

bot = Bot(token=BOT_TOKEN)
seen_tokens = set()

SOURCES = {
    "FirstLedger": "https://firstledger.net/api/tokens",
    "XPMarket": "https://api.xpmarket.com/v1/tokens",
    "HorizonXRPL": "https://api.horizonxrpl.com/tokens"
}

# ----------------------------
# Core Functions
# ----------------------------
async def check_new_tokens():
    global seen_tokens
    logging.info("🔍 Running token check across sources...")
    for name, url in SOURCES.items():
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()

            tokens = data.get("tokens") or data
            logging.info(f"{name} returned {len(tokens)} tokens")

            for token in tokens:
                symbol = token.get("symbol") or token.get("currency")
                issuer = token.get("issuer")
                if not symbol or not issuer:
                    continue

                token_id = f"{symbol}:{issuer}"

                if token_id not in seen_tokens:
                    seen_tokens.add(token_id)
                    msg = (
                        f"🚀 New Token Detected on XRPL\n"
                        f"🪙 Name: {symbol}\n"
                        f"💳 Issuer: {issuer}\n"
                        f"📊 Source: {name}\n"
                        f"🔗 View: {url}"
                    )
                    logging.info(f"📢 Sending alert for {token_id}")
                    await bot.send_message(chat_id=CHAT_ID, text=msg)

        except Exception as e:
            logging.error(f"Error fetching from {name}: {e}")

async def self_ping():
    """Ping our own health check endpoint to prevent Render from sleeping."""
    while True:
        try:
            requests.get(APP_URL, timeout=5)
            logging.info("🌐 Self-ping successful")
        except Exception as e:
            logging.error(f"Self-ping failed: {e}")
        await asyncio.sleep(300)  # every 5 minutes

# ----------------------------
# Flask health check
# ----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "XRPL Token Alert Bot is running ✅"

# ----------------------------
# Scheduler
# ----------------------------
async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_tokens, "interval", minutes=2)
    scheduler.start()
    logging.info("🚀 Scheduler started")

    # Start self-ping
    asyncio.create_task(self_ping())

    # Send startup + test message
    try:
        await bot.send_message(chat_id=CHAT_ID, text="✅ XRPL Token Alert Bot is live on Render!")
        await bot.send_message(chat_id=CHAT_ID, text="🧪 Test Alert: This confirms Telegram notifications are working.")
    except Exception as e:
        logging.error(f"Failed to send startup/test message: {e}")

# ----------------------------
# Entrypoint
# ----------------------------
def run():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(start_scheduler())

    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=False)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    loop.run_forever()

if __name__ == "__main__":
    run()
