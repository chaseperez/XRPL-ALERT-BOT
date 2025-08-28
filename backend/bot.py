import os
import logging
import requests
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from flask import Flask
from threading import Thread

# Load environment variables
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
APP_URL = os.getenv("APP_URL")  # Add your Render app URL here for self-ping

if not BOT_TOKEN or not CHAT_ID or not APP_URL:
    raise RuntimeError("❌ BOT_TOKEN, CHAT_ID, or APP_URL missing in environment variables!")

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
    logging.info("🔍 Starting token check across sources...")
    for name, url in SOURCES.items():
        try:
            logging.info(f"📡 Fetching tokens from {name} ({url})")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            tokens = data.get("tokens") or data
            logging.info(f"✅ {name} returned {len(tokens)} tokens")

            for token in tokens:
                symbol = token.get("symbol") or token.get("currency")
                issuer = token.get("issuer")
                token_id = f"{symbol}:{issuer}"

                if not symbol or not issuer:
                    logging.warning(f"⚠️ Skipping malformed token from {name}: {token}")
                    continue

                if token_id not in seen_tokens:
                    logging.info(f"🆕 New token found on {name}: {token_id}")
                    seen_tokens.add(token_id)

                    msg = (
                        f"🚀 New Token Detected on XRPL\n"
                        f"🪙 Name: {symbol}\n"
                        f"💳 Issuer: {issuer}\n"
                        f"📊 Source: {name}\n"
                        f"🔗 View: {url}"
                    )
                    try:
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        logging.info(f"✅ Sent alert for {symbol}:{issuer}")
                    except Exception as e:
                        logging.error(f"❌ Failed to send Telegram message: {e}")

        except Exception as e:
            logging.error(f"❌ Error fetching from {name}: {e}")


async def self_ping():
    """Ping our own health check endpoint to prevent Render from sleeping."""
    while True:
        try:
            logging.info("🌐 Sending self-ping...")
            resp = requests.get(APP_URL, timeout=5)
            logging.info(f"🌐 Self-ping response: {resp.status_code}")
        except Exception as e:
            logging.error(f"❌ Self-ping failed: {e}")
        await asyncio.sleep(300)  # ping every 5 minutes


# Flask app for Render health check
app = Flask(__name__)

@app.route("/")
def home():
    logging.info("💓 Health check hit")
    return "XRPL Token Alert Bot is running ✅"


async def start_scheduler():
    logging.info("🕒 Initializing scheduler...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_tokens, "interval", minutes=2)
    scheduler.start()
    logging.info("🚀 Scheduler started successfully")

    # Start self-ping loop
    logging.info("🌐 Starting self-ping loop")
    asyncio.create_task(self_ping())

    # Send startup message to Telegram
    try:
        await bot.send_message(chat_id=CHAT_ID, text="✅ XRPL Token Alert Bot is live on Render!")
        logging.info("📩 Startup message sent to Telegram")
    except Exception as e:
        logging.error(f"❌ Failed to send startup message: {e}")


def run():
    logging.info("⚡ Bot is starting up...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start the scheduler in the event loop
    loop.create_task(start_scheduler())

    # Run Flask in a separate thread so the loop keeps running
    def run_flask():
        logging.info("🌐 Starting Flask webserver for health check...")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=False)

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Keep the asyncio loop alive
    logging.info("🌀 Entering asyncio loop...")
    loop.run_forever()


if __name__ == "__main__":
    run()
