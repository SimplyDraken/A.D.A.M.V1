import os
import time
import requests
from dotenv import load_dotenv

from database import get_connection
from telegram_bot import (
    answer_callback_query,
    send_telegram_message,
    edit_telegram_message_with_buttons,
    edit_menu_message
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = str(os.getenv("CHAT_ID"))

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================
# TELEGRAM UI HELPERS
# =========================

def send_message_with_keyboard(chat_id, text, keyboard):

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": keyboard
        }
    }

    response = requests.post(
        url,
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


# =========================
# TELEGRAM UPDATE SYSTEM
# =========================

def get_updates(offset=None):

    url = f"{BASE_URL}/getUpdates"

    params = {
        "timeout": 30
    }

    if offset:
        params["offset"] = offset

    response = requests.get(
        url,
        params=params,
        timeout=35
    )

    response.raise_for_status()

    return response.json()


# =========================
# DATABASE HELPERS
# =========================

def get_recent_events(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_recent_alerts(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?",
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_status_summary():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) AS total FROM events"
    )

    total_events = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COUNT(*) AS total FROM alerts"
    )

    total_alerts = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM alerts
        WHERE status = 'pending'
        """
    )

    pending_alerts = cursor.fetchone()["total"]

    conn.close()

    return total_events, total_alerts, pending_alerts


# =========================
# ALERT HELPERS
# =========================

def extract_alert_id(message_text):

    try:
        first_line = message_text.splitlines()[0]
        return int(first_line.split("#")[1])

    except Exception:
        return None


def format_alert_card(
    alert_id,
    reason,
    status,
    action,
    risk="HIGH",
    extra_line=None
):

    text = (
        f"🚨 A.D.A.M SECURITY ALERT #{alert_id}\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"⚠️ Threat Level: {risk}\n"
        f"📍 Status: {status}\n"
        f"⚙️ Action: {action}\n\n"
        f"🧠 Reasoning:\n{reason}"
    )

    if extra_line:
        text += f"\n\n{extra_line}"

    return text


def normalize_action(action):

    mapping = {
        "acknowledge": "Acknowledge",
        "trigger_alarm": "Trigger Alarm",
        "lockdown": "Lockdown",
        "ignore": "Ignore",
        "override_alarm": "Override Alarm",
        "override_lockdown": "Override Lockdown",
        "mark_safe": "Mark Safe"
    }

    return mapping.get(
        action,
        action.replace("_", " ").title()
    )


def apply_action_transition(current_status, action):

    if current_status == "pending":

        if action in [
            "acknowledge",
            "trigger_alarm",
            "lockdown",
            "ignore"
        ]:
            return "resolved", action

    elif current_status in [
        "resolved",
        "overridden"
    ]:

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

    cursor.execute(
        """
        SELECT status,
               alert_message,
               telegram_message_id
        FROM alerts
        WHERE id = ?
        """,
        (alert_id,)
    )

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    previous_status = row["status"]
    reason = row["alert_message"]
    telegram_message_id = row["telegram_message_id"]

    new_status, final_action = apply_action_transition(
        previous_status,
        action
    )

    cursor.execute(
        """
        UPDATE alerts
        SET status = ?, chosen_action = ?
        WHERE id = ?
        """,
        (
            new_status,
            final_action,
            alert_id
        )
    )

    conn.commit()
    conn.close()

    return {
        "alert_id": alert_id,
        "reason": reason,
        "telegram_message_id": telegram_message_id,
        "new_status": new_status,
        "new_action": final_action
    }


# =========================
# CONTROL PANEL
# =========================

def get_home_keyboard():

    return [
        [
            {
                "text": "📊 Dashboard",
                "callback_data": "dashboard"
            },
            {
                "text": "🚨 Alerts",
                "callback_data": "alerts"
            }
        ],
        [
            {
                "text": "📡 Devices",
                "callback_data": "devices"
            },
            {
                "text": "🧠 Intelligence",
                "callback_data": "intelligence"
            }
        ],
        [
            {
                "text": "⚙️ Controls",
                "callback_data": "controls"
            }
        ]
    ]


def get_navigation_keyboard():

    return [
        [
            {
                "text": "📊 Dashboard",
                "callback_data": "dashboard"
            },
            {
                "text": "🚨 Alerts",
                "callback_data": "alerts"
            }
        ],
        [
            {
                "text": "📡 Devices",
                "callback_data": "devices"
            },
            {
                "text": "🧠 Intelligence",
                "callback_data": "intelligence"
            }
        ],
        [
            {
                "text": "⚙️ Controls",
                "callback_data": "controls"
            }
        ],
        [
            {
                "text": "🏠 Home",
                "callback_data": "home"
            }
        ]
    ]


def send_control_panel(chat_id):

    send_message_with_keyboard(
        chat_id,
        (
            "🤖 A.D.A.M SECURITY CORE\n"
            "━━━━━━━━━━━━━━━\n\n"
            "🟢 Core Status: ONLINE\n"
            "⚠️ Threat Level: NORMAL\n"
            "📡 Monitoring Active\n\n"
            "A.D.A.M is actively supervising\n"
            "your connected environment.\n\n"
            "Select an interface module below."
        ),
        get_home_keyboard()
    )


# =========================
# COMMAND HANDLER
# =========================

def handle_command(chat_id, text):

    if str(chat_id) != OWNER_CHAT_ID:

        send_telegram_message(
            "Unauthorized operator."
        )

        return

    if text == "/start":
        send_control_panel(chat_id)


# =========================
# BOT RUNTIME
# =========================

def run_bot():

    print("A.D.A.M v1 is now live...")

    last_update_id = None

    while True:

        try:

            updates = get_updates(last_update_id)

            if updates.get("ok"):

                for item in updates.get("result", []):

                    last_update_id = (
                        item["update_id"] + 1
                    )

                    # =========================
                    # CALLBACK BUTTONS
                    # =========================

                    if "callback_query" in item:

                        cq = item["callback_query"]

                        callback_id = cq["id"]
                        action = cq["data"]

                        message = cq["message"]

                        message_id = message["message_id"]

                        message_text = message["text"]

                        chat_id = str(
                            message["chat"]["id"]
                        )

                        if chat_id != OWNER_CHAT_ID:

                            answer_callback_query(
                                callback_id,
                                "Unauthorized"
                            )

                            continue

                        # =========================
                        # HOME
                        # =========================

                        if action == "home":

                            edit_menu_message(
                                message_id,
                                (
                                    "🤖 A.D.A.M SECURITY CORE\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "🟢 Core Status: ONLINE\n"
                                    "⚠️ Threat Level: NORMAL\n"
                                    "📡 Monitoring Active\n\n"
                                    "A.D.A.M is actively supervising\n"
                                    "your connected environment.\n\n"
                                    "Select an interface module below."
                                ),
                                get_home_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Control panel loaded"
                            )

                            continue

                        # =========================
                        # DASHBOARD
                        # =========================

                        elif action == "dashboard":

                            total_events, total_alerts, pending_alerts = (
                                get_status_summary()
                            )

                            edit_menu_message(
                                message_id,
                                (
                                    "📊 SYSTEM DASHBOARD\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "🟢 Core Status: ONLINE\n"
                                    f"📡 Events Logged: {total_events}\n"
                                    f"🚨 Alerts Generated: {total_alerts}\n"
                                    f"🟡 Pending Alerts: {pending_alerts}\n\n"
                                    "🧠 Adaptive Intelligence Active"
                                ),
                                get_navigation_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Dashboard loaded"
                            )

                            continue

                        # =========================
                        # ALERTS
                        # =========================

                        elif action == "alerts":

                            rows = get_recent_alerts()

                            if not rows:

                                alert_text = (
                                    "🚨 ACTIVE ALERTS\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "🟢 No active threats detected."
                                )

                            else:

                                alert_text = (
                                    "🚨 ACTIVE ALERTS\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                )

                                for r in rows:

                                    alert_text += (
                                        f"🚨 Alert #{r['id']}\n"
                                        f"📍 Status: {r['status'].upper()}\n"
                                        f"🧠 Reason: {r['alert_message']}\n"
                                        f"⚙️ Action: {r['chosen_action']}\n\n"
                                    )

                            edit_menu_message(
                                message_id,
                                alert_text,
                                get_navigation_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Alerts loaded"
                            )

                            continue

                        # =========================
                        # DEVICES
                        # =========================

                        elif action == "devices":

                            edit_menu_message(
                                message_id,
                                (
                                    "📡 DEVICE CENTER\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "Connected Devices: 4\n\n"
                                    "📷 Cameras: 2\n"
                                    "🚪 Sensors: 2\n\n"
                                    "🟢 All monitored devices are operational."
                                ),
                                get_navigation_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Devices loaded"
                            )

                            continue

                        # =========================
                        # INTELLIGENCE
                        # =========================

                        elif action == "intelligence":

                            edit_menu_message(
                                message_id,
                                (
                                    "🧠 A.D.A.M INTELLIGENCE CORE\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "Adaptive behavioral monitoring is active.\n\n"
                                    "A.D.A.M is currently learning:\n"
                                    "• activity timing\n"
                                    "• device behavior\n"
                                    "• operational patterns\n"
                                    "• environmental deviations"
                                ),
                                get_navigation_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Intelligence loaded"
                            )

                            continue

                        # =========================
                        # CONTROLS
                        # =========================

                        elif action == "controls":

                            edit_menu_message(
                                message_id,
                                (
                                    "⚙️ SECURITY CONTROLS\n"
                                    "━━━━━━━━━━━━━━━\n\n"
                                    "🚨 Alarm Systems\n"
                                    "🔒 Lockdown Systems\n"
                                    "📡 Device Monitoring\n"
                                    "🧠 Adaptive Monitoring"
                                ),
                                get_navigation_keyboard()
                            )

                            answer_callback_query(
                                callback_id,
                                "Controls loaded"
                            )

                            continue

                        # =========================
                        # ALERT ACTIONS
                        # =========================

                        alert_id = extract_alert_id(
                            message_text
                        )

                        result = None

                        if alert_id is not None:

                            result = update_alert_status(
                                alert_id,
                                action
                            )

                        if result:

                            if result["new_status"] in [
                                "resolved",
                                "overridden"
                            ]:
                                button_mode = "override"

                            elif result["new_status"] == "closed":
                                button_mode = "none"

                            else:
                                button_mode = "pending"

                            extra_line = None

                            if result["new_status"] == "closed":

                                extra_line = (
                                    "🟢 Incident closed."
                                )

                            new_text = format_alert_card(
                                alert_id=result["alert_id"],
                                reason=result["reason"],
                                status=result["new_status"].upper(),
                                action=normalize_action(
                                    result["new_action"]
                                ),
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

                                print(
                                    "Edit message error:",
                                    e
                                )

                            answer_callback_query(
                                callback_id,
                                f"{normalize_action(result['new_action'])} applied"
                            )

                    # =========================
                    # COMMAND HANDLING
                    # =========================

                    elif "message" in item:

                        msg = item["message"]

                        chat_id = msg["chat"]["id"]

                        text = msg.get(
                            "text",
                            ""
                        ).strip().lower()

                        if text.startswith("/"):

                            handle_command(
                                chat_id,
                                text
                            )

            time.sleep(0.5)

        except Exception as e:

            print("Bot error:", e)

            time.sleep(2)


if __name__ == "__main__":
    run_bot()