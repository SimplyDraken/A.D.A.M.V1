import time
from datetime import datetime, timedelta
from database import get_connection
from telegram_bot import send_telegram_message, edit_telegram_message_with_buttons


def get_alert_by_id(alert_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def parse_timestamp(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def choose_auto_action(alert_message: str) -> str:
    msg = alert_message.lower()

    if "motion detected in restricted hours" in msg:
        return "shut_doors_and_trigger_fire_alarm"
    if "door opened during restricted hours" in msg:
        return "advanced_locking"
    if "high temperature detected" in msg:
        return "alert_owner"

    return "log_and_review"


def pretty_action_name(action: str) -> str:
    return action.replace("_", " ").title()


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

def process_pending_alerts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM alerts
        WHERE status = 'pending'
        ORDER BY id ASC
    """)
    alerts = cursor.fetchall()

    now = datetime.now()

    for alert in alerts:
        created_at = parse_timestamp(alert["created_at"])
        if not created_at:
            continue

        if now - created_at >= timedelta(seconds=20):
            action = choose_auto_action(alert["alert_message"])

            cursor.execute("""
                UPDATE alerts
                SET status = ?, chosen_action = ?
                WHERE id = ?
            """, ("auto_escalated", action, alert["id"]))

            updated_text = format_alert_card(
                alert_id=alert["id"],
                reason=alert["alert_message"],
                status="AUTO-ESCALATED",
                action=pretty_action_name(action),
                risk="HIGH",
                extra_line="Human override is still allowed."
            )

            if alert["telegram_message_id"]:
                try:
                    edit_telegram_message_with_buttons(
                        alert["telegram_message_id"],
                        updated_text,
                        button_mode="override"
                    )
                except Exception as e:
                    print(f"Edit message error for alert #{alert['id']}: {e}")

    conn.commit()
    conn.close()


def run_auto_responder():
    print("A.D.A.M auto responder is running...")
    while True:
        try:
            process_pending_alerts()
            time.sleep(10)
        except Exception as e:
            print("Auto responder error:", e)
            time.sleep(10)


if __name__ == "__main__":
    run_auto_responder()