from datetime import datetime


def analyze_event(event: dict) -> dict:
    sensor_type = event.get("sensor_type")
    value = str(event.get("value"))
    location = event.get("location", "").lower()
    timestamp = event.get("timestamp")

    try:
        hour = datetime.fromisoformat(timestamp).hour
    except Exception:
        hour = 12

    anomaly = 0
    risk_level = "low"
    action_taken = "log_only"
    reason = "Normal activity"
    confidence_score = 0.50
    decision_basis = "No unusual condition detected"

    if sensor_type == "motion":
        if value == "1":
            if location in ["lab", "server_room", "office"] and (hour < 6 or hour > 20):
                anomaly = 1
                risk_level = "high"
                action_taken = "send_alert"
                reason = "Motion detected in restricted hours"
                confidence_score = 0.92
                decision_basis = "Restricted-hour motion + sensitive location"
            elif location == "hallway":
                anomaly = 0
                risk_level = "low"
                action_taken = "log_only"
                reason = "Hallway motion is considered safe"
                confidence_score = 0.78
                decision_basis = "Expected motion zone"
            else:
                anomaly = 0
                risk_level = "low"
                action_taken = "log_only"
                reason = "Normal motion event"
                confidence_score = 0.72
                decision_basis = "Motion detected in non-sensitive context"

    elif sensor_type == "door":
        if value == "1" and (hour < 6 or hour > 20):
            anomaly = 1
            risk_level = "critical"
            action_taken = "trigger_alarm"
            reason = "Door opened during restricted hours"
            confidence_score = 0.96
            decision_basis = "Unauthorized entry pattern + restricted-hour access"

    elif sensor_type == "temperature":
        try:
            temp = float(value)
            if temp > 50:
                anomaly = 1
                risk_level = "high"
                action_taken = "send_alert"
                reason = "High temperature detected"
                confidence_score = 0.89
                decision_basis = "Temperature exceeds high-risk threshold"
            elif temp < 10:
                anomaly = 1
                risk_level = "medium"
                action_taken = "log_and_review"
                reason = "Unusually low temperature detected"
                confidence_score = 0.76
                decision_basis = "Temperature below expected safe range"
            else:
                anomaly = 0
                risk_level = "low"
                action_taken = "log_only"
                reason = "Temperature within normal range"
                confidence_score = 0.81
                decision_basis = "Temperature within expected operating range"
        except ValueError:
            reason = "Invalid temperature value"
            confidence_score = 0.40
            decision_basis = "Sensor value could not be parsed"

    return {
        "anomaly": anomaly,
        "risk_level": risk_level,
        "action_taken": action_taken,
        "reason": reason,
        "confidence_score": confidence_score,
        "decision_basis": decision_basis
    }