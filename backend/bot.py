# backend/bot.py

import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Dispatcher
from apscheduler.schedulers.background import BackgroundScheduler
import httpx

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN missing")

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram bot
bot = Bot(token=BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()
dispatcher: Dispatcher = application.dispatcher

# -----------------------
# Telegram Command Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the XRPL Wallet Tracker Bot!")

dispatcher.add_handler(CommandHandler("start", start))

# -----------------------
# Scheduler / Tracking Logic
# -----------------------
scheduler = BackgroundScheduler()

def fetch_tokens():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bot/1.0"}
        response = httpx.get("https://firstledger.net/api/tokens", headers=headers, timeout=10)
        response.raise_for_status()
        tokens = response.json()
        logger.info(f"✅ Fetched {len(tokens)} tokens")
        # TODO: process tokens and send Telegram alerts
    except httpx.HTTPStatusError as e:
        logger.error(f"🌐 FirstLedger HTTP error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error fetching tokens: {e}")

# Run every 30 seconds
scheduler.add_job(fetch_tokens, "interval", seconds=30)
scheduler.start()

# -----------------------
# Flask Routes for Telegram Webhook
# -----------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

# Health check for Render
@app.route("/")
def health():
    return jsonify({"status": "ok"}), 200

# -----------------------
# Run Flask
# -----------------------
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)
