# 🚀 XRPL Token Alert Bot

A Telegram bot that tracks **newly launched tokens on the XRPL** and sends alerts to your Telegram.  
The bot monitors:

- [FirstLedger](https://firstledger.net)
- [XPMarket](https://xpmarket.com)
- [HorizonXRPL](https://horizonxrpl.com)

Whenever a new token is detected, you’ll get a message in Telegram like:


---

## 🔧 Features
- Tracks tokens across **multiple XRPL explorers**
- Sends alerts directly to **Telegram**
- Runs 24/7 on **Render free tier**
- Lightweight and async (Flask + APScheduler + python-telegram-bot)
- Sends **startup message** to Telegram on deploy
- Provides a **health check endpoint** (`/`) for Render
- Gunicorn-ready for production deployment

---

## ⚡ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/chaseperez/xrpl-alert-bot.git
cd xrpl-token-alert-bot/backend
