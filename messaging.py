from twilio.rest import Client
import requests
import config

client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

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