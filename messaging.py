from twilio.rest import Client
import requests
import config
from datetime import datetime

client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

SHOP_NAME = "Jitender and Brothers"

def send_whatsapp(to_number, message):
    try:
        client.messages.create(
            from_=config.TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to_number}",
            body=message
        )
        print(f"WhatsApp sent to {to_number}")
    except Exception as e:
        print(f"WhatsApp failed: {e}")

def send_sms(to_number, message):
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "message": message,
            "language": "english",
            "route": "q",
            "numbers": to_number,
        }
        headers = {
            "authorization": "your_fast2sms_api_key_here",
            "Content-Type": "application/json"
        }
        requests.post(url, json=payload, headers=headers)
        print(f"SMS sent to {to_number}")
    except Exception as e:
        print(f"SMS failed: {e}")

def send_message(phone, channel, message):
    if channel == "whatsapp":
        send_whatsapp(phone, message)
    else:
        send_sms(phone, message)

def msg_daily_purchase(name, amount, balance):
    return (
        f"Hello {name},\n"
        f"🛒 Purchase Update ({datetime.now().strftime('%d %b %Y')})\n"
        f"Today's Purchase: ₹{amount:.0f}\n"
        f"Total Outstanding Balance: ₹{balance:.0f}\n"
        f"Thank you for choosing {SHOP_NAME}."
    )

def msg_payment_received(name, paid_amount, balance):
    return (
        f"Hello {name},\n"
        f"✅ Payment Received ({datetime.now().strftime('%d %b %Y')})\n"
        f"Payment Received: ₹{paid_amount:.0f}\n"
        f"Total Outstanding Balance: ₹{balance:.0f}\n"
        f"We appreciate your payment.\n"
        f"Thank you for choosing {SHOP_NAME}."
    )

# def msg_limit_exceeded(name, balance, limit):
#     return (
#         f"Hello {name},\n"
#         f"⚠️ Credit Limit Alert\n"
#         f"Your total outstanding balance is ₹{balance:.0f}.\n"
#         f"This exceeds your credit limit of ₹{limit:.0f}.\n"
#         f"Please make a payment at your earliest convenience.\n"
#         f"Thank you for choosing {SHOP_NAME}."
#     )

def msg_month_end(name, balance):
    return (
        f"Hello {name},\n"
        f"📋 Monthly Balance Reminder ({datetime.now().strftime('%B %Y')})\n"
        f"Total Outstanding Balance: ₹{balance:.0f}\n"
        f"Please clear your outstanding balance at your earliest convenience.\n"
        f"Thank you for choosing {SHOP_NAME}."
    )

def msg_purchase_and_limit_exceeded(name, amount, balance, limit):
    return (
        f"Hello {name},\n"
        f"⚠️ Credit Limit Alert ({datetime.now().strftime('%d %b %Y')})\n"
        f"Today's Purchase: ₹{amount:.0f}\n"
        f"Total Outstanding Balance: ₹{balance:.0f}\n"
        f"Your balance has exceeded your credit limit of ₹{limit:.0f}.\n"
        f"Please make a payment at your earliest convenience.\n"
        f"Thank you for choosing {SHOP_NAME}."
    )