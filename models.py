import datetime
import sqlite3


def get_db():
    """Open a DB connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT
            )"""
        )

        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "email" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                date TEXT NOT NULL,
                revealed_at TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(username, date)
            )"""
        )
        conn.commit()


def get_utc_now():
    """Return timezone-aware current UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


def today_str():
    """Return today's UTC date as YYYY-MM-DD string."""
    return get_utc_now().date().isoformat()


def get_today_activity(username):
    """Return today's activity row for a user, or None."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM activity WHERE username=? AND date=?",
            (username, today_str()),
        )
        return cursor.fetchone()


def calculate_streaks(username):
    """Return (current_streak, best_streak) based on consecutive UTC days."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date FROM activity WHERE username=? ORDER BY date DESC",
            (username,),
        )
        rows = cursor.fetchall()

    if not rows:
        return 0, 0

    unique_dates = sorted(
        {datetime.date.fromisoformat(row["date"]) for row in rows},
        reverse=True
    )

    today = get_utc_now().date()
    yesterday = today - datetime.timedelta(days=1)
    has_current_streak = unique_dates[0] in (today, yesterday)

    current_streak = 0
    best_streak = 0
    run = 1

    for i in range(len(unique_dates)):
        if i < len(unique_dates) - 1 and unique_dates[i] - unique_dates[i + 1] == datetime.timedelta(days=1):
            run += 1
        else:
            best_streak = max(best_streak, run)
            if has_current_streak and current_streak == 0:
                current_streak = run
            run = 1

    return current_streak, best_streak