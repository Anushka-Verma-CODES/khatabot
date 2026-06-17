# KhataBot

A WhatsApp-based credit tracking system for small kirana stores. The merchant logs credit sales via a simple WhatsApp command. Customers receive automated notifications for every purchase, credit limit breaches, and month-end reminders.

Built as a POC for Jitender and Brothers, Kasauli.

---

## The Problem

Small grocery stores give goods on credit to regular customers but track everything manually — in registers or memory. This leads to:

- Delayed collections because dues go unnoticed
- Customers unaware of their outstanding balance
- Owner spending 1.5–2 hours/day on manual tracking and follow-up calls

---

## The Solution

A two-sided WhatsApp system:

**Merchant side** — owner texts `Ramesh 500` to a WhatsApp bot. Balance updates instantly. No app to open, no form to fill.

**Customer side** — customer receives an automatic WhatsApp (or SMS) notification for every transaction, a credit limit alert when they cross their limit, and a month-end reminder.

**Dashboard** — merchant resolves escalated queries and broadcasts offers from a simple web UI.

---

## Features

- Log credit by texting `Name Amount` (e.g. `Ramesh 500`)
- Auto-creates new customers on first transaction
- Real-time balance tracking per customer
- Purchase notification sent to customer on every transaction
- Combined purchase + credit limit alert when limit is crossed
- Month-end balance reminders to all customers
- SUMMARY command for owner to see all outstanding balances
- Merchant dashboard with live customer balances
- Broadcast offers and announcements to all or select customers
- Dual-channel delivery — WhatsApp primary, SMS fallback via Fast2SMS

---

## Tech Stack

- Python + Flask
- SQLite
- Twilio WhatsApp Business API
- Fast2SMS (SMS fallback)
- APScheduler (scheduled reminders)
- ngrok (local tunnel for development)

---

## Project Structure

```
khatabot/
├── app.py            # Flask app, webhook, dashboard routes
├── db.py             # SQLite setup and queries
├── messaging.py      # Twilio WhatsApp + Fast2SMS + message templates
├── config.py         # Credentials and settings (not committed)
├── config.example.py # Template for config setup
└── requirements.txt  # Dependencies
```

---

## Setup

**1. Clone the repo**
```
git clone https://github.com/Anushka-Verma-CODES/khatabot.git
cd khatabot
```

**2. Create virtual environment**
```
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies**
```
pip install flask twilio apscheduler requests
```

**4. Configure credentials**

Copy `config.example.py` to `config.py` and fill in your values:
```
TWILIO_ACCOUNT_SID = "your_account_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
DEFAULT_CREDIT_LIMIT = 2000
```

**5. Start ngrok**
```
ngrok http 5000
```

**6. Set webhook URL in Twilio**

Go to Twilio Console → Messaging → Sandbox Settings → set "When a message comes in" to:
```
https://your-ngrok-url.ngrok-free.dev/webhook
```

**7. Run the app**
```
python app.py
```

---

## Usage

**Log a credit sale:**
```
Ramesh 500
```

**Check all outstanding balances:**
```
SUMMARY
```

**View dashboard:**
```
http://localhost:5000/dashboard
```

**Add customer phone number:**
```python
python update_phone.py
```

---

## WhatsApp Commands

| Command | Description |
|---------|-------------|
| `Name Amount` | Log credit (e.g. Ramesh 500) |
| `SUMMARY` | View all outstanding balances |
| `MENU` | Show available commands |

---

## Known Limitations

- Twilio sandbox has a 50 messages/day limit. Production deployment uses a verified WhatsApp Business number with no such restriction.
- Customers must join the Twilio sandbox before receiving messages in development. Not required in production.
- ngrok URL changes on every restart — update Twilio webhook URL accordingly.

---

## Merchant

Jitender and Brothers
Grocery / Kirana, Kasauli, Himachal Pradesh