import os
import json
import logging
import asyncio
from threading import Thread
from pathlib import Path
from typing import Any, Dict, List, Iterable, Tuple

import httpx
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from flask import Flask

# ----------------------------
# Setup
# ----------------------------
load_dotenv()
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
APP_URL = os.getenv("APP_URL")  # Render app URL

if not BOT_TOKEN or not CHAT_ID or not APP_URL:
    raise RuntimeError("❌ BOT_TOKEN, CHAT_ID, or APP_URL missing in environment variables!")

bot = Bot(token=BOT_TOKEN)

# Persist seen tokens
DATA_DIR = Path(os.getenv("DATA_DIR", "backend"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEEN_FILE = DATA_DIR / "seen_tokens.json"

def load_seen() -> set:
    try:
        if SEEN_FILE.exists():
            with SEEN_FILE.open("r", encoding="utf-8") as f:
                tokens = set(json.load(f))
                logging.debug(f"Loaded {len(tokens)} previously seen tokens")
                return tokens
    except Exception as e:
        logging.error(f"Failed to load seen tokens: {e}")
    return set()

def save_seen(s: set) -> None:
    try:
        with SEEN_FILE.open("w", encoding="utf-8") as f:
            json.dump(sorted(s), f)
        logging.debug(f"Saved {len(s)} seen tokens")
    except Exception as e:
        logging.error(f"Failed to save seen tokens: {e}")

seen_tokens = load_seen()

# XRPL token sources
SOURCES: Dict[str, str] = {
    "FirstLedger": "https://firstledger.net/api/tokens",
    "XPMarket": "https://api.xpmarket.com/v1/tokens",
    "HorizonXRPL": "https://api.horizonxrpl.com/tokens",
}

# ----------------------------
# Helpers
# ----------------------------
def _first(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return None

def normalize_tokens(source: str, payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        candidates = payload.get("tokens") or payload.get("data") or payload.get("items") or payload.get("result")
        if isinstance(candidates, list):
            logging.debug(f"{source}: normalized to list of {len(candidates)} tokens")
            return candidates
        if isinstance(candidates, dict):
            logging.debug(f"{source}: single token dict detected")
            return [candidates]
        for v in payload.values():
            if isinstance(v, list):
                logging.debug(f"{source}: found list in values with {len(v)} tokens")
                return v
        return []
    if isinstance(payload, list):
        logging.debug(f"{source}: payload is already a list of {len(payload)} tokens")
        return payload
    logging.debug(f"{source}: payload could not be normalized")
    return []

def extract_symbol_issuer(token: Dict[str, Any]) -> Tuple[str, str]:
    symbol = _first(token, ["symbol", "currency", "code", "ticker", "name"])
    issuer = _first(token, ["issuer", "issuerAddress", "issuer_address", "issuer_raddress", "account",
                            "issuerAccount", "issuer_account"])
    if symbol: symbol = str(symbol).strip()
    if issuer: issuer = str(issuer).strip()
    return symbol, issuer

async def http_get_json(client: httpx.AsyncClient, url: str) -> Any:
    logging.debug(f"HTTP GET {url}")
    r = await client.get(url)
    logging.debug(f"Response status {r.status_code} from {url}")
    r.raise_for_status()
    return r.json()

async def send_msg(text: str) -> None:
    logging.debug(f"Sending Telegram message: {text[:50]}...")
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
        logging.info("📩 Telegram message sent")
    except Exception as e:
        logging.error(f"❌ Telegram send failed: {e}")

# ----------------------------
# Core tasks
# ----------------------------
async def check_new_tokens():
    global seen_tokens
    logging.info("🔍 Running token check...")
    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for name, url in SOURCES.items():
            try:
                logging.info(f"📡 Fetching from {name} -> {url}")
                data = await http_get_json(client, url)
                tokens = normalize_tokens(name, data)
                logging.info(f"✅ {name}: {len(tokens)} tokens received")

                new_count = 0
                for token in tokens:
                    symbol, issuer = extract_symbol_issuer(token)
                    logging.debug(f"{name}: parsed token {symbol}:{issuer}")
                    if not symbol or not issuer:
                        continue

                    token_id = f"{symbol}:{issuer}"
                    if token_id not in seen_tokens:
                        seen_tokens.add(token_id)
                        new_count += 1
                        save_seen(seen_tokens)

                        msg = (
                            f"🚀 New Token Detected on XRPL\n"
                            f"🪙 Name: {symbol}\n"
                            f"💳 Issuer: {issuer}\n"
                            f"📊 Source: {name}\n"
                            f"🔗 View: {url}"
                        )
                        logging.info(f"📢 Alerting for {token_id}")
                        await send_msg(msg)

                logging.info(f"📊 {name}: {new_count} new tokens this run")

            except httpx.HTTPError as he:
                logging.error(f"🌐 {name} HTTP error: {he}")
            except Exception as e:
                logging.error(f"❌ {name} unexpected error: {e}")

async def self_ping():
    timeout = httpx.Timeout(10)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        while True:
            try:
                r = await client.get(APP_URL)
                logging.info(f"💓 Self-ping {r.status_code}")
            except Exception as e:
                logging.error(f"❌ Self-ping failed: {e}")
            await asyncio.sleep(300)

# ----------------------------
# Flask health check
# ----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    logging.info("✅ Health check hit")
    return "XRPL Token Alert Bot is running ✅"

# ----------------------------
# Scheduler
# ----------------------------
async def start_scheduler():
    logging.info("🕒 Initializing scheduler...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_tokens, "interval", minutes=2, id="token_check", max_instances=1)
    scheduler.start()
    logging.info("🚀 Scheduler started")

    asyncio.create_task(self_ping())

    # Startup confirms
    await send_msg("✅ XRPL Token Alert Bot is live on Render!")
    await send_msg("🧪 Test Alert: Telegram notifications are working.")

# ----------------------------
# Entrypoint
# ----------------------------
def run():
    logging.info("⚡ Booting bot event loop...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(start_scheduler())

    def run_flask():
        logging.info("🌐 Starting Flask server...")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), use_reloader=False)

    Thread(target=run_flask, daemon=True).start()
    loop.run_forever()

if __name__ == "__main__":
    run()
else:
    Thread(target=run, daemon=True).start()
