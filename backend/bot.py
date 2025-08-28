import os
import logging
import requests
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from flask import Flask

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN or CHAT_ID missing in environment variables!")

bot = Bot(token=BOT_TOKEN)

# Store seen tokens
seen_tokens = set()

# Token listing APIs
SOURCES = {
    "FirstLedger": "https://firstledger.net/api/tokens",
    "XPMarket": "https://api.xpmarket.com/v1/tokens",
    "HorizonXRPL": "https://api.horizonxrpl.com/tokens"
}

async def check_new_tokens():
    global seen_tokens
    for name, url in SOURCES.items():
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()

            # Adjust parsing based on API structure
            tokens = data.get("tokens") or data  

            for token in tokens:
                symbol = token.get("symbol") or token.get("currency")
                issuer = token.get("issuer")
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
                    await bot.send_message(chat_id=CHAT_ID, text=msg)

        except Exception as e:
            logging.error(f"Error fetching from {name}: {e}")

# Flask app for Render health check
app = Flask(__name__)

@app.route("/")
def home():
    return "XRPL Token Alert Bot is running ✅"

# Scheduler setup
async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_tokens, "interval", minutes=2)
    scheduler.start()
    logging.info("🚀 Scheduler started")

    # Send startup message
    try:
        await bot.send_message(chat_id=CHAT_ID, text="✅ XRPL Token Alert Bot is live on Render!")
    except Exception as e:
        logging.error(f"Failed to send startup message: {e}")

# Initialize background scheduler when Gunicorn starts
def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.create_task(start_scheduler())
    loop.run_forever()

# Gunicorn entry point
def init_scheduler():
    loop = asyncio.new_event_loop()
    import threading
    t = threading.Thread(target=start_background_loop, args=(loop,))
    t.start()

# Run this if executing directly (for local testing)
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_scheduler())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=False)
