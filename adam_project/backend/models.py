from datetime import datetime
from rules import analyze_event
from database import get_connection


def save_event(event, analysis):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (
            device_id,
            sensor_type,
            value,
            location,
            timestamp,
            anomaly,
            risk_level,
            action_taken
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event["device_id"],
        event["sensor_type"],
        str(event["value"]),
        event["location"],
        event["timestamp"],
        analysis["anomaly"],
        analysis["risk_level"],
        analysis["action_taken"]
    ))

    conn.commit()
    conn.close()


# Test event
sample_event = {
    "device_id": "pir_001",
    "sensor_type": "motion",
    "value": 1,
    "location": "lab",
    "timestamp": datetime.now().isoformat()
}

analysis = analyze_event(sample_event)

# Save to DB
save_event(sample_event, analysis)

print("Event:", sample_event)
print("Analysis:", analysis)
print("✅ Event saved to database")