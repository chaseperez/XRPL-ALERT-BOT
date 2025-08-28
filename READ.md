# 🚀 XRPL Token Alert Bot

A lightweight async Telegram bot that **tracks new token listings across multiple XRPL explorers** and sends instant alerts to Telegram.  

✅ Runs 24/7 on **Render free tier** with **no external uptime monitor needed** (built-in self-ping).  
✅ Sends **startup message** when deployed successfully.  
✅ Includes **health check endpoint** (`/`) for Render.  

---




## 🔧 Features
- Tracks tokens from:
  - FirstLedger
  - XPMarket
  - HorizonXRPL
- Tracks tokens across **multiple XRPL explorers**
- Sends alerts directly to **Telegram**
- Runs 24/7 on **Render free tier**
- Built-in **self-ping task** (no UptimeRobot required)
- Async + lightweight (Flask + APScheduler + python-telegram-bot)
- Sends **startup message** to Telegram on deploy
- Provides a **health check endpoint** (`/`) for Render
- Deploy-ready on **Render**
- Gunicorn-ready for production deployment

---

## ⚡ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/chaseperez/xrpl-alert-bot.git
cd xrpl-alert-bot/backend