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
OWNER_CHAT_ID = str(os.getenv("CHAT_ID"))
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}

    if offset:
        params["offset"] = offset

    response = requests.get(url, params=params, timeout=35)
    response.raise_for_status()
    return response.json()


def get_alert_by_id(alert_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_recent_events(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_recent_alerts(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_status_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM events")
    total_events = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM alerts")
    total_alerts = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM alerts WHERE status = 'pending'")
    pending_alerts = cursor.fetchone()["total"]

    conn.close()

    return total_events, total_alerts, pending_alerts


def extract_alert_id(message_text):
    try:
        first_line = message_text.splitlines()[0]
        return int(first_line.split("#")[1])
    except Exception:
        return None


def format_alert_card(alert_id, reason, status, action, risk="HIGH", confidence=None, basis=None, extra_line=None):
    text = (
        f"🚨 A.D.A.M SECURITY ALERT #{alert_id}\n"
        f"Reason: {reason}\n"
        f"Risk: {risk}\n"
        f"Status: {status}\n"
        f"Action: {action}"
    )

    if confidence is not None:
        text += f"\nConfidence: {confidence}%"

    if basis:
        text += f"\nDecision Basis: {basis}"

    if extra_line:
        text += f"\n{extra_line}"

    return text

def normalize_action(action):
    mapping = {
        "acknowledge": "Acknowledge",
        "trigger_alarm": "Trigger Alarm",
        "lockdown": "Lockdown",
        "ignore": "Ignore",
        "override_alarm": "Override Alarm",
        "override_lockdown": "Override Lockdown",
        "mark_safe": "Mark Safe",
        "shut_doors_and_trigger_fire_alarm": "Shut Doors And Trigger Fire Alarm",
        "advanced_locking": "Advanced Locking",
        "alert_owner": "Alert Owner"
    }
    return mapping.get(action, action.replace("_", " ").title())


def apply_action_transition(current_status, action):
    if current_status == "pending":
        if action in ["acknowledge", "trigger_alarm", "lockdown", "ignore"]:
            return "resolved", action
    elif current_status in ["auto_escalated", "resolved", "overridden"]:
        if action == "override_alarm":
            return "overridden", "trigger_alarm"
        elif action == "override_lockdown":
            return "overridden", "lockdown"
        elif action == "mark_safe":
            return "closed", "mark_safe"

    return current_status, action


def update_alert_status(alert_id, action):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status, chosen_action, alert_message, telegram_message_id FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    previous_status = row["status"]
    previous_action = row["chosen_action"]
    reason = row["alert_message"]
    telegram_message_id = row["telegram_message_id"]

    new_status, final_action = apply_action_transition(previous_status, action)

    cursor.execute("""
        UPDATE alerts
        SET status = ?, chosen_action = ?
        WHERE id = ?
    """, (new_status, final_action, alert_id))

    conn.commit()
    conn.close()

    return {
        "alert_id": alert_id,
        "reason": reason,
        "telegram_message_id": telegram_message_id,
        "previous_status": previous_status,
        "previous_action": previous_action,
        "new_status": new_status,
        "new_action": final_action
    }


def handle_command(chat_id, text):
    if str(chat_id) != OWNER_CHAT_ID:
        send_telegram_message("Unauthorized operator.")
        return

    if text == "/start":
        send_telegram_message(
            "🤖 A.D.A.M CONTROL PANEL, built by DRAKEN 🐉\n\n"
            "Commands:\n"
            "/status\n"
            "/events\n"
            "/alerts\n"
            "/lastalert\n"
            "/help"
        )

    elif text == "/help":
        send_telegram_message(
            "🧠 A.D.A.M Operator Guide\n\n"
            "/status - System health\n"
            "/events - Recent events\n"
            "/alerts - Recent alerts\n"
            "/lastalert - Latest alert"
        )

    elif text == "/status":
        total_events, total_alerts, pending_alerts = get_status_summary()
        send_telegram_message(
            "📊 A.D.A.M STATUS\n"
            f"Events: {total_events}\n"
            f"Alerts: {total_alerts}\n"
            f"Pending Alerts: {pending_alerts}\n"
            "System State: Active"
        )

    elif text == "/events":
        rows = get_recent_events()
        if not rows:
            send_telegram_message("No events found.")
        else:
            msg = "📋 Recent Events:\n"
            for r in rows:
                msg += (
                    f"#{r['id']} | {r['sensor_type']} | "
                    f"{r['location']} | Risk: {r['risk_level']} | {r['timestamp']}\n"
                )
            send_telegram_message(msg)

    elif text == "/alerts":
        rows = get_recent_alerts()
        if not rows:
            send_telegram_message("No alerts found.")
        else:
            msg = "🚨 Recent Alerts:\n"
            for r in rows:
                msg += (
                    f"#{r['id']} | {r['status']} | "
                    f"{r['alert_message']} | Action: {r['chosen_action']}\n"
                )
            send_telegram_message(msg)

    elif text == "/lastalert":
        rows = get_recent_alerts(limit=1)
        if not rows:
            send_telegram_message("No alert found.")
        else:
            r = rows[0]
            send_telegram_message(
                f"🚨 Latest Alert #{r['id']}\n"
                f"Reason: {r['alert_message']}\n"
                f"Status: {r['status']}\n"
                f"Action: {r['chosen_action']}"
            )


def run_bot():
    print("A.D.A.M v1 is now live...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)

            if updates.get("ok"):
                for item in updates.get("result", []):
                    last_update_id = item["update_id"] + 1

                    # BUTTON HANDLING
                    if "callback_query" in item:
                        cq = item["callback_query"]
                        callback_id = cq["id"]
                        action = cq["data"]
                        message = cq["message"]
                        message_text = message["text"]
                        chat_id = str(message["chat"]["id"])

                        if chat_id != OWNER_CHAT_ID:
                            answer_callback_query(callback_id, "Unauthorized")
                            continue

                        alert_id = extract_alert_id(message_text)
                        result = None

                        if alert_id is not None:
                            result = update_alert_status(alert_id, action)

                        if result:
                            if result["new_status"] in ["resolved", "auto_escalated", "overridden"]:
                                button_mode = "override"
                            elif result["new_status"] == "closed":
                                button_mode = "none"
                            else:
                                button_mode = "pending"

                            extra_line = None
                            if result["new_status"] == "auto_escalated":
                                extra_line = "Human override is still allowed."
                            elif result["new_status"] == "closed":
                                extra_line = "Incident closed."

                            new_text = format_alert_card(
                                alert_id=result["alert_id"],
                                reason=result["reason"],
                                status=result["new_status"].upper(),
                                action=normalize_action(result["new_action"]),
                                risk="HIGH",
                                extra_line=extra_line
                            )

                            try:
                                edit_telegram_message_with_buttons(
                                    result["telegram_message_id"],
                                    new_text,
                                    button_mode=button_mode
                                )
                            except Exception as e:
                                print("Edit message error:", e)

                            answer_callback_query(
                                callback_id,
                                f"{normalize_action(result['new_action'])} applied"
                            )

                    # COMMAND HANDLING
                    elif "message" in item:
                        msg = item["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip().lower()

                        if text.startswith("/"):
                            handle_command(chat_id, text)

            time.sleep(0.5)

        except Exception as e:
            print("Bot error:", e)
            time.sleep(2)


if __name__ == "__main__":
    run_bot()