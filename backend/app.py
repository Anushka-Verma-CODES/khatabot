import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel
import db
import messaging

load_dotenv()

app = FastAPI(title="KhataBot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_CREDIT_LIMIT = int(os.environ.get("DEFAULT_CREDIT_LIMIT_RS", 2000))

@app.on_event("startup")
def startup():
    db.init_db()

# ─── API: customers ──────────────────────────────────────────────────────────

class CustomerIn(BaseModel):
    name: str
    phone: str
    channel: str = "whatsapp"
    credit_limit_rupees: float = 2000.0
    opening_balance_rupees: float = 0.0

@app.post("/api/customers", status_code=201)
def add_customer(data: CustomerIn):
    name    = data.name.strip()
    phone   = data.phone.strip()
    channel = data.channel

    if not name or not phone:
        return JSONResponse({"error": "name and phone are required"}, status_code=400)
    if channel not in ("whatsapp", "sms"):
        return JSONResponse({"error": "channel must be whatsapp or sms"}, status_code=400)

    credit_limit_paise    = round(data.credit_limit_rupees * 100)
    opening_balance_paise = round(data.opening_balance_rupees * 100)

    conn = db.get_db()
    try:
        conn.execute(
            "INSERT INTO customers (name, phone, channel, credit_limit_paise, opening_balance_paise) VALUES (?,?,?,?,?)",
            (name, phone, channel, credit_limit_paise, opening_balance_paise)
        )
        conn.commit()
        customer_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"id": customer_id, "name": name, "phone": phone}
    except Exception as e:
        conn.rollback()
        if "UNIQUE constraint failed: customers.phone" in str(e):
            return JSONResponse({"error": "Phone number already registered"}, status_code=409)
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        conn.close()

@app.get("/api/customers")
def list_customers():
    conn = db.get_db()
    rows = conn.execute(
        "SELECT id, name, phone, channel, credit_limit_paise FROM customers ORDER BY name"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        balance_paise = db.get_balance(r["id"])
        result.append({
            "id": r["id"],
            "name": r["name"],
            "phone": r["phone"],
            "channel": r["channel"],
            "balance_rupees": balance_paise / 100,
            "credit_limit_rupees": r["credit_limit_paise"] / 100,
            "over_limit": balance_paise > r["credit_limit_paise"],
        })
    return result

# ─── Twilio webhook ──────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    from twilio.twiml.messaging_response import MessagingResponse
    incoming = Body.strip()
    resp = MessagingResponse()

    parts = incoming.split()
    name, amount = None, None
    if len(parts) == 2:
        try:
            name = parts[0].capitalize()
            amount = float(parts[1])
        except ValueError:
            name, amount = None, None

    if name and amount:
        conn = db.get_db()
        customer = conn.execute(
            "SELECT * FROM customers WHERE name = ?", (name,)
        ).fetchone()

        if not customer:
            resp.message(f"Customer '{name}' not found. Add them via the dashboard first.")
            conn.close()
            return HTMLResponse(str(resp), media_type="text/xml")

        amount_paise = round(amount * 100)
        conn.execute(
            "INSERT INTO transactions (customer_id, amount_paise, type) VALUES (?,?,?)",
            (customer["id"], amount_paise, "credit")
        )
        conn.commit()

        balance_paise = db.get_balance(customer["id"])
        balance_rs = balance_paise / 100
        limit_rs   = customer["credit_limit_paise"] / 100

        reply = f"Logged: {name} owes Rs.{amount:.0f} more. Total: Rs.{balance_rs:.0f}"

        if customer["phone"]:
            if balance_paise > customer["credit_limit_paise"]:
                reply += f"\n⚠️ {name} has crossed the limit of Rs.{limit_rs:.0f}!"
                messaging.send_message(
                    customer["phone"], customer["channel"],
                    messaging.msg_limit_exceeded(name, amount, balance_rs, limit_rs)
                )
            else:
                messaging.send_message(
                    customer["phone"], customer["channel"],
                    messaging.msg_credit(name, amount, balance_rs)
                )
        conn.close()
        resp.message(reply)

    elif incoming.lower() == "summary":
        conn = db.get_db()
        customers = conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
        conn.close()
        if customers:
            lines = ["Outstanding balances:"]
            for c in customers:
                bal = db.get_balance(c["id"]) / 100
                lines.append(f"  {c['name']}: Rs.{bal:.0f}")
            resp.message("\n".join(lines))
        else:
            resp.message("No customers yet.")

    elif incoming.lower() == "menu":
        resp.message(
            "KhataBot Menu:\n"
            "Log credit: Name Amount (e.g. Ramesh 500)\n"
            "SUMMARY: see all balances"
        )

    else:
        conn = db.get_db()
        conn.execute("INSERT INTO queries (message) VALUES (?)", (incoming,))
        conn.commit()
        conn.close()
        resp.message("Command not recognised. Type MENU for options.")

    return HTMLResponse(str(resp), media_type="text/xml")

# ─── Dashboard ───────────────────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>KhataBot Dashboard</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
  th { background: #f5f5f5; }
  .over { color: #c0392b; font-weight: bold; }
  .query-box { background: #fff9e6; padding: 15px; margin: 10px 0; border-left: 4px solid #f0a500; }
  input, textarea, select { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
  button { background: #25d366; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; }
  .section { margin: 30px 0; }
  #add-msg { margin-top: 8px; font-size: 14px; }
</style>
</head>
<body>
<h2>KhataBot — Jitender and Brothers</h2>

<div class="section">
  <h3>Add Customer</h3>
  <input id="cname" placeholder="Full name" />
  <input id="cphone" placeholder="Phone (10 digits, no +91)" maxlength="10" />
  <select id="cchannel">
    <option value="whatsapp">WhatsApp</option>
    <option value="sms">SMS</option>
  </select>
  <input id="climit" placeholder="Credit limit (Rs)" type="number" value="2000" />
  <input id="copening" placeholder="Opening balance (Rs) — existing dues before KhataBot" type="number" value="0" />
  <button onclick="addCustomer()">Add Customer</button>
  <p id="add-msg"></p>
</div>

<div class="section">
  <h3>Customer Balances</h3>
  <table>
    <tr><th>Name</th><th>Phone</th><th>Channel</th><th>Balance</th><th>Limit</th><th>Status</th></tr>
    {% for c in customers %}
    <tr>
      <td>{{ c.name }}</td>
      <td>{{ c.phone }}</td>
      <td>{{ c.channel }}</td>
      <td>Rs.{{ "%.0f"|format(c.balance_rs) }}</td>
      <td>Rs.{{ "%.0f"|format(c.limit_rs) }}</td>
      <td class="{{ 'over' if c.over_limit else '' }}">{{ '⚠️ Over limit' if c.over_limit else 'OK' }}</td>
    </tr>
    {% endfor %}
  </table>
</div>

<div class="section">
  <h3>Open Queries</h3>
  {% for q in queries %}
  <div class="query-box">
    <strong>Query #{{ q.id }}</strong> — {{ q.created_at }}<br>
    {{ q.message }}<br><br>
    <form method="POST" action="/reply">
      <input type="hidden" name="query_id" value="{{ q.id }}">
      <textarea name="reply_text" rows="2" placeholder="Type your reply..."></textarea>
      <button type="submit">Send Reply</button>
    </form>
  </div>
  {% endfor %}
  {% if not queries %}<p>No open queries.</p>{% endif %}
</div>

<div class="section">
  <h3>Broadcast Message</h3>
  <form method="POST" action="/broadcast">
    <textarea name="message" rows="3" placeholder="Type offer or announcement..."></textarea><br>
    <button type="submit">Send to All Customers</button>
  </form>
</div>

<script>
async function addCustomer() {
  const msg = document.getElementById('add-msg');
  msg.style.color = 'black';
  msg.textContent = 'Saving...';
  const res = await fetch('/api/customers', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      name: document.getElementById('cname').value,
      phone: '+91' + document.getElementById('cphone').value,
      channel: document.getElementById('cchannel').value,
      credit_limit_rupees: parseFloat(document.getElementById('climit').value) || 2000,
      opening_balance_rupees: parseFloat(document.getElementById('copening').value) || 0
    })
  });
  const data = await res.json();
  if (res.ok) {
    msg.style.color = 'green';
    msg.textContent = data.name + ' added successfully.';
    setTimeout(() => location.reload(), 1000);
  } else {
    msg.style.color = 'red';
    msg.textContent = data.error;
  }
}
</script>
</body>
</html>
"""

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    from jinja2 import Template
    conn = db.get_db()
    rows    = conn.execute("SELECT id, name, phone, channel, credit_limit_paise FROM customers ORDER BY name").fetchall()
    queries = conn.execute("SELECT * FROM queries WHERE status = 'open' ORDER BY created_at DESC").fetchall()
    conn.close()

    customers = []
    for r in rows:
        bal_paise = db.get_balance(r["id"])
        customers.append({
            "name": r["name"],
            "phone": r["phone"],
            "channel": r["channel"],
            "balance_rs": bal_paise / 100,
            "limit_rs": r["credit_limit_paise"] / 100,
            "over_limit": bal_paise > r["credit_limit_paise"],
        })

    queries_list = [dict(q) for q in queries]
    return Template(DASHBOARD_HTML).render(customers=customers, queries=queries_list)

@app.post("/reply")
async def reply(query_id: str = Form(...), reply_text: str = Form(...)):
    conn = db.get_db()
    conn.execute("UPDATE queries SET status = 'resolved' WHERE id = ?", (query_id,))
    conn.commit()
    conn.close()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/broadcast")
async def broadcast(message: str = Form(...)):
    conn = db.get_db()
    customers = conn.execute("SELECT phone, channel FROM customers").fetchall()
    conn.close()
    for c in customers:
        messaging.send_message(c["phone"], c["channel"], message)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard", status_code=303)

# ─── Scheduler ───────────────────────────────────────────────────────────────

def send_month_end_reminders():
    if datetime.now().day == 28:
        conn = db.get_db()
        customers = conn.execute(
            "SELECT id, name, phone, channel FROM customers WHERE phone IS NOT NULL"
        ).fetchall()
        conn.close()
        for c in customers:
            bal_rs = db.get_balance(c["id"]) / 100
            if bal_rs > 0:
                messaging.send_message(
                    c["phone"], c["channel"],
                    messaging.msg_month_end(c["name"], bal_rs)
                )

scheduler = BackgroundScheduler()
scheduler.add_job(send_month_end_reminders, "cron", hour=9, minute=0)
scheduler.start()
