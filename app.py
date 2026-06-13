from flask import Flask, request, render_template_string
from twilio.twiml.messaging_response import MessagingResponse
from apscheduler.schedulers.background import BackgroundScheduler
import db
import messaging
import config
from datetime import datetime

app = Flask(__name__)
db.init_db()

def parse_command(text):
    parts = text.strip().split()
    if len(parts) == 2:
        name = parts[0].capitalize()
        try:
            amount = float(parts[1])
            return name, amount
        except ValueError:
            return None, None
    return None, None

def get_or_create_customer(name):
    conn = db.get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE name = ?", (name,)
    ).fetchone()
    if not customer:
        conn.execute(
            "INSERT INTO customers (name, credit_limit) VALUES (?, ?)",
            (name, config.DEFAULT_CREDIT_LIMIT)
        )
        conn.commit()
        customer = conn.execute(
            "SELECT * FROM customers WHERE name = ?", (name,)
        ).fetchone()
    conn.close()
    return customer

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming = request.form.get("Body", "").strip()
    sender = request.form.get("From", "").replace("whatsapp:", "")
    resp = MessagingResponse()

    name, amount = parse_command(incoming)

    if name and amount:
        conn = db.get_db()
        customer = get_or_create_customer(name)

        new_balance = customer["balance"] + amount
        conn.execute(
            "UPDATE customers SET balance = ? WHERE name = ?",
            (new_balance, name)
        )
        conn.execute(
            "INSERT INTO transactions (customer_name, amount, type) VALUES (?, ?, ?)",
            (name, amount, "credit")
        )
        conn.commit()

        reply = f"Logged: {name} owes Rs.{amount:.0f} more. Total: Rs.{new_balance:.0f}"

        # Send daily purchase notification + alert to customer
    
        if new_balance > customer["credit_limit"]:
            reply += f"\n⚠️ {name} has crossed the credit limit of Rs.{customer['credit_limit']:.0f}!"
            if customer["phone"]:
                messaging.send_message(
                    customer["phone"], customer["channel"],
                    messaging.msg_purchase_and_limit_exceeded(name, amount, new_balance, customer["credit_limit"])
                )
        else:
            if customer["phone"]:
                messaging.send_message(
                    customer["phone"], customer["channel"],
                    messaging.msg_daily_purchase(name, amount, new_balance)
                )

        conn.close()
        resp.message(reply)

    elif incoming.lower() == "menu":
        resp.message("KhataBot Menu:\n1. Reply with customer name + amount to log credit (e.g. Ramesh 500)\n2. Type SUMMARY for today's overview\n3. Type BROADCAST to send an offer to all customers")

    elif incoming.lower() == "summary":
        conn = db.get_db()
        customers = conn.execute("SELECT name, balance FROM customers ORDER BY balance DESC").fetchall()
        conn.close()
        if customers:
            lines = ["Outstanding balances:"]
            for c in customers:
                lines.append(f"  {c['name']}: Rs.{c['balance']:.0f}")
            resp.message("\n".join(lines))
        else:
            resp.message("No customers yet.")

    else:
        conn = db.get_db()
        conn.execute(
            "INSERT INTO queries (customer_name, message) VALUES (?, ?)",
            ("owner_query", incoming)
        )
        conn.commit()
        conn.close()
        resp.message("Command not recognised. Type MENU for options.")

    return str(resp)

def send_month_end_reminders():
    today = datetime.now()
    if today.day == 28:
        conn = db.get_db()
        customers = conn.execute(
            "SELECT * FROM customers WHERE phone IS NOT NULL AND balance > 0"
        ).fetchall()
        conn.close()
        for customer in customers:
            msg = messaging.msg_month_end(customer["name"], customer["balance"])
            messaging.send_message(customer["phone"], customer["channel"], msg)

scheduler = BackgroundScheduler()
scheduler.add_job(send_month_end_reminders, "cron", hour=9, minute=0)
scheduler.start()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>KhataBot Dashboard</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
  th { background: #f5f5f5; }
  .query-box { background: #fff9e6; padding: 15px; margin: 10px 0; border-left: 4px solid #f0a500; }
  input, textarea { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
  button { background: #25d366; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; }
</style>
</head>
<body>
<h2>KhataBot Merchant Dashboard</h2>

<h3>Customer Balances</h3>
<table>
  <tr><th>Name</th><th>Balance</th><th>Limit</th><th>Status</th></tr>
  {% for c in customers %}
  <tr>
    <td>{{ c['name'] }}</td>
    <td>Rs.{{ "%.0f"|format(c['balance']) }}</td>
    <td>Rs.{{ "%.0f"|format(c['credit_limit']) }}</td>
    <td>{% if c['balance'] > c['credit_limit'] %}⚠️ Over limit{% else %}OK{% endif %}</td>
  </tr>
  {% endfor %}
</table>

<h3>Open Queries</h3>
{% for q in queries %}
<div class="query-box">
  <strong>{{ q['customer_name'] }}</strong> — {{ q['timestamp'] }}<br>
  {{ q['message'] }}<br><br>
  <form method="POST" action="/reply">
    <input type="hidden" name="query_id" value="{{ q['id'] }}">
    <input type="hidden" name="customer_name" value="{{ q['customer_name'] }}">
    <textarea name="reply_text" rows="2" placeholder="Type your reply..."></textarea>
    <button type="submit">Send Reply</button>
  </form>
</div>
{% endfor %}

<h3>Broadcast Message</h3>
<form method="POST" action="/broadcast">
  <textarea name="message" rows="3" placeholder="Type offer or announcement..."></textarea><br>
  <button type="submit">Send to All Customers</button>
</form>
</body>
</html>
"""

@app.route("/dashboard")
def dashboard():
    conn = db.get_db()
    customers = conn.execute("SELECT * FROM customers ORDER BY balance DESC").fetchall()
    queries = conn.execute("SELECT * FROM queries WHERE status = 'open' ORDER BY timestamp DESC").fetchall()
    conn.close()
    return render_template_string(DASHBOARD_HTML, customers=customers, queries=queries)

@app.route("/reply", methods=["POST"])
def reply():
    query_id = request.form.get("query_id")
    customer_name = request.form.get("customer_name")
    reply_text = request.form.get("reply_text")
    conn = db.get_db()
    customer = conn.execute("SELECT * FROM customers WHERE name = ?", (customer_name,)).fetchone()
    if customer and customer["phone"]:
        messaging.send_message(customer["phone"], customer["channel"], reply_text)
    conn.execute("UPDATE queries SET status = 'resolved' WHERE id = ?", (query_id,))
    conn.commit()
    conn.close()
    return '<script>window.location="/dashboard"</script>'

@app.route("/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message")
    conn = db.get_db()
    customers = conn.execute("SELECT * FROM customers WHERE phone IS NOT NULL").fetchall()
    conn.close()
    for customer in customers:
        messaging.send_message(customer["phone"], customer["channel"], message)
    return '<script>window.location="/dashboard"</script>'

if __name__ == "__main__":
    app.run(debug=True, port=5000)