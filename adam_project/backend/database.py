import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "adam.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value TEXT NOT NULL,
    location TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    anomaly INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'low',
    action_taken TEXT DEFAULT 'log_only',
    confidence_score REAL DEFAULT 0.0,
    decision_basis TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    alert_message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    telegram_message_id TEXT,
    chosen_action TEXT,
    FOREIGN KEY (event_id) REFERENCES events (id)
)
""")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")