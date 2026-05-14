import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_telegram_message(message: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def send_alert_with_buttons(message: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Acknowledge", "callback_data": "acknowledge"},
                    {"text": "🚨 Alarm", "callback_data": "trigger_alarm"}
                ],
                [
                    {"text": "🔒 Lockdown", "callback_data": "lockdown"},
                    {"text": "❌ Ignore", "callback_data": "ignore"}
                ]
            ]
        }
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def edit_telegram_message_with_buttons(message_id: str, new_text: str, button_mode: str = "override"):
    url = f"{BASE_URL}/editMessageText"

    if button_mode == "pending":
        keyboard = [
            [
                {"text": "✅ Acknowledge", "callback_data": "acknowledge"},
                {"text": "🚨 Alarm", "callback_data": "trigger_alarm"}
            ],
            [
                {"text": "🔒 Lockdown", "callback_data": "lockdown"},
                {"text": "❌ Ignore", "callback_data": "ignore"}
            ]
        ]
    elif button_mode == "override":
        keyboard = [
            [
                {"text": "🚨 Override Alarm", "callback_data": "override_alarm"},
                {"text": "🔒 Override Lockdown", "callback_data": "override_lockdown"}
            ],
            [
                {"text": "🟢 Mark Safe", "callback_data": "mark_safe"}
            ]
        ]
    else:
        keyboard = []

    payload = {
        "chat_id": CHAT_ID,
        "message_id": int(message_id),
        "text": new_text,
        "reply_markup": {
            "inline_keyboard": keyboard
        }
    }

    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def answer_callback_query(callback_query_id, text="Action received"):
    url = f"{BASE_URL}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": text
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()