import os
import time
import requests
from dotenv import load_dotenv
from database import get_connection
from telegram_bot import (
    answer_callback_query,
    send_telegram_message,
    edit_telegram_message_with_buttons,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def format_alert_message(alert_id, event_text, risk="HIGH", status="PENDING", action="None"):
    return (
        f"🚨 A.D.A.M Alert #{alert_id}\n"
        f"{event_text}\n"
        f"Risk: {risk}\n"
        f"Status: {status}\n"
        f"Action: {action}"
    )


def get_alert_by_id(alert_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()

    conn.close()
    return row


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}

    if offset:
        params["offset"] = offset

    response = requests.get(url, params=params, timeout=35)
    response.raise_for_status()
    return response.json()


def update_alert_status(alert_id, action):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, chosen_action FROM alerts WHERE id = ?",
        (alert_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    current_status = row["status"]
    previous_action = row["chosen_action"]

    if current_status == "pending":
        new_status = "resolved"
    elif current_status == "auto_escalated":
        new_status = "overridden"
    else:
        new_status = current_status

    cursor.execute("""
        UPDATE alerts
        SET status = ?, chosen_action = ?
        WHERE id = ?
    """, (new_status, action, alert_id))

    conn.commit()
    conn.close()

    return {
        "previous_status": current_status,
        "previous_action": previous_action,
        "new_status": new_status,
        "new_action": action
    }


def extract_alert_id(message_text):
    try:
        first_line = message_text.splitlines()[0]
        # Example: "🚨 A.D.A.M Alert #3"
        return int(first_line.split("#")[1])
    except Exception:
        return None


def run_button_handler():
    print("A.D.A.M button handler is running...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)

            if updates.get("ok"):
                for item in updates.get("result", []):
                    last_update_id = item["update_id"] + 1

                    callback_query = item.get("callback_query")
                    if not callback_query:
                        continue

                    callback_id = callback_query["id"]
                    action = callback_query["data"]
                    message = callback_query["message"]
                    message_text = message["text"]

                    alert_id = extract_alert_id(message_text)

                    result = None
                    alert_row = None

                    if alert_id is not None:
                        result = update_alert_status(alert_id, action)
                        alert_row = get_alert_by_id(alert_id)

                    if alert_row and alert_row["telegram_message_id"] and result:
                        new_text = (
                            f"🚨 A.D.A.M Alert #{alert_id}\n"
                            f"Reason: {alert_row['alert_message']}\n"
                            f"Status: {result['new_status'].upper()}\n"
                            f"Action: {result['new_action']}"
                        )

                        try:
                            edit_telegram_message_with_buttons(
                                alert_row["telegram_message_id"],
                                new_text
                            )
                        except Exception as e:
                            print("Edit message error:", e)

                    answer_callback_query(callback_id, f"Action selected: {action}")

                    if result:
                        if result["previous_status"] == "auto_escalated":
                            send_telegram_message(
                                f"🧠 Human Override Recorded\n"
                                f"Alert ID: {alert_id}\n"
                                f"Previous Status: {result['previous_status']}\n"
                                f"Previous Action: {result['previous_action']}\n"
                                f"New Status: {result['new_status']}\n"
                                f"New Action: {result['new_action']}"
                            )
                        else:
                            send_telegram_message(
                                f"🧠 A.D.A.M Response\n"
                                f"Alert ID: {alert_id}\n"
                                f"New Status: {result['new_status']}\n"
                                f"Chosen Action: {result['new_action']}"
                            )

            time.sleep(2)

        except Exception as e:
            print("Button handler error:", e)
            time.sleep(5)


if __name__ == "__main__":
    run_button_handler()