import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# The database file will be created in the project's main folder.
DB_PATH = Path(__file__).resolve().parent.parent / "monitor.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to the database file."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row  # lets us read columns by name
    return connection


def now_utc() -> str:
    """Current time in UTC as text, e.g. 2026-10-07T10:00:00+00:00"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    connection = get_connection()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                check_type TEXT NOT NULL,
                host TEXT,
                port INTEGER,
                url TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                is_up INTEGER NOT NULL,
                latency_ms REAL,
                status_code INTEGER,
                error TEXT,
                FOREIGN KEY (target_id) REFERENCES targets (id)
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def add_target(name: str, check_type: str, host: str = None,
               port: int = None, url: str = None) -> int:
    """Insert a new target and return its id."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            "INSERT INTO targets (name, check_type, host, port, url, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, check_type, host, port, url, now_utc()),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def list_targets() -> list:
    """Return all targets as a list of dictionaries."""
    connection = get_connection()
    try:
        rows = connection.execute("SELECT * FROM targets ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def save_result(target_id: int, is_up: bool, latency_ms: float = None,
                status_code: int = None, error: str = None) -> None:
    """Store the outcome of one check."""
    connection = get_connection()
    try:
        connection.execute(
            "INSERT INTO check_results "
            "(target_id, checked_at, is_up, latency_ms, status_code, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (target_id, now_utc(), 1 if is_up else 0,
             latency_ms, status_code, error),
        )
        connection.commit()
    finally:
        connection.close()


def get_recent_results(target_id: int, limit: int = 20) -> list:
    """Return the newest results for one target."""
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM check_results WHERE target_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (target_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


if __name__ == "__main__":
    # Quick self-test: create tables, add a target, save a result, read it back.
    init_db()
    new_id = add_target("Google DNS", "ping", host="8.8.8.8")
    save_result(new_id, is_up=True, latency_ms=23.0)
    print("Targets:", list_targets())
    print("Results:", get_recent_results(new_id))