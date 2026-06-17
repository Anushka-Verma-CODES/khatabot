import os
import requests
from twilio.rest import Client
from datetime import datetime

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
FAST2SMS_API_KEY   = os.environ.get("FAST2SMS_API_KEY", "")
SHOP_NAME          = os.environ.get("SHOP_NAME", "Jitender and Brothers")

def send_whatsapp(to_number, message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to_number}",
            body=message
        )
        print(f"[WhatsApp] sent to {to_number}")
    except Exception as e:
        print(f"[WhatsApp] failed for {to_number}: {e}")

def send_sms(to_number, message):
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "variables_values": message,
            "route": "q",
            "numbers": to_number.replace("+91", ""),
        }
        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json"
        }
        res = requests.post(url, json=payload, headers=headers)
        print(f"[SMS] sent to {to_number}: {res.json()}")
    except Exception as e:
        print(f"[SMS] failed for {to_number}: {e}")

def send_message(phone, channel, message):
    if channel == "whatsapp":
        send_whatsapp(phone, message)
    else:
        send_sms(phone, message)

def msg_credit(name, amount_rs, balance_rs):
    return (
        f"Hello {name},\n"
        f"Purchase update ({datetime.now().strftime('%d %b %Y')})\n"
        f"Today's purchase: Rs.{amount_rs:.0f}\n"
        f"Outstanding balance: Rs.{balance_rs:.0f}\n"
        f"Thank you - {SHOP_NAME}"
    )

def msg_limit_exceeded(name, amount_rs, balance_rs, limit_rs):
    return (
        f"Hello {name},\n"
        f"Credit limit alert ({datetime.now().strftime('%d %b %Y')})\n"
        f"Today's purchase: Rs.{amount_rs:.0f}\n"
        f"Outstanding balance: Rs.{balance_rs:.0f}\n"
        f"This exceeds your limit of Rs.{limit_rs:.0f}.\n"
        f"Please make a payment soon.\n"
        f"Thank you - {SHOP_NAME}"
    )

def msg_payment_received(name, paid_rs, balance_rs):
    return (
        f"Hello {name},\n"
        f"Payment received: Rs.{paid_rs:.0f}\n"
        f"Remaining balance: Rs.{balance_rs:.0f}\n"
        f"Thank you - {SHOP_NAME}"
    )

def msg_month_end(name, balance_rs):
    return (
        f"Hello {name},\n"
        f"Monthly reminder ({datetime.now().strftime('%B %Y')})\n"
        f"Outstanding balance: Rs.{balance_rs:.0f}\n"
        f"Please clear dues at your earliest convenience.\n"
        f"Thank you - {SHOP_NAME}"
    )
