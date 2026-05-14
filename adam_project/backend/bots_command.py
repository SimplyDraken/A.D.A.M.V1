import os
import time
import requests
from dotenv import load_dotenv
from database import get_connection

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=payload, timeout=15)
    return response.json()


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=35)
    return response.json()


def get_status():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM events")
    total_events = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM alerts")
    total_alerts = cursor.fetchone()["total"]

    conn.close()

    return (
        "🤖 A.D.A.M Status\n"
        f"Total Events: {total_events}\n"
        f"Total Alerts: {total_alerts}\n"
        "System State: Active"
    )


def get_recent_events(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No events found."

    lines = ["📋 Recent Events:"]
    for row in rows:
        lines.append(
            f"#{row['id']} | {row['sensor_type']} | {row['location']} | "
            f"Risk: {row['risk_level']} | {row['timestamp']}"
        )

    return "\n".join(lines)


def get_recent_alerts(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No alerts found."

    lines = ["🚨 Recent Alerts:"]
    for row in rows:
        lines.append(
            f"#{row['id']} | {row['alert_message']} | {row['created_at']}"
        )

    return "\n".join(lines)


def get_last_alert():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "No alert found."

    return (
        "🚨 Last Alert\n"
        f"ID: {row['id']}\n"
        f"Message: {row['alert_message']}\n"
        f"Time: {row['created_at']}"
    )


def handle_command(chat_id, text):
    text = text.strip().lower()

    if text == "/start":
        return send_message(
            chat_id,
            "🤖 A.D.A.M Bot Online\n\nCommands:\n/status\n/events\n/alerts\n/lastalert"
        )

    elif text == "/status":
        return send_message(chat_id, get_status())

    elif text == "/events":
        return send_message(chat_id, get_recent_events())

    elif text == "/alerts":
        return send_message(chat_id, get_recent_alerts())

    elif text == "/lastalert":
        return send_message(chat_id, get_last_alert())

    else:
        return send_message(
            chat_id,
            "Unknown command.\nUse:\n/status\n/events\n/alerts\n/lastalert"
        )


def run_bot():
    print("A.D.A.M Telegram command bot is running...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get("ok"):
                for item in updates.get("result", []):
                    last_update_id = item["update_id"] + 1

                    message = item.get("message")
                    if not message:
                        continue

                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")

                    print(f"Received: {text} from {chat_id}")
                    handle_command(chat_id, text)

            time.sleep(2)

        except Exception as e:
            print("Bot error:", e)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()