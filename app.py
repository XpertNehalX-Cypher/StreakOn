# app.py
import os
import calendar

from flask import Flask, jsonify, redirect, render_template, request, session
from dotenv import load_dotenv
import datetime
from models import get_db, init_db, get_utc_now, today_str, get_today_activity, calculate_streaks
from auth import auth_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key")
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=21)
app.register_blueprint(auth_bp)

init_db()


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    session["username"] = username
    logged_in = "username" in session
    return render_template("index.html", logged_in=logged_in)


@app.route("/base")
def base():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    activity = get_today_activity(username)
    revealed_at = None
    completed = False

    if activity:
        revealed_at = activity["revealed_at"]
        completed = bool(activity["completed"])

    current_streak, best_streak = calculate_streaks(username)

    today = get_utc_now()
    _, num_days = calendar.monthrange(today.year, today.month)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, completed FROM activity WHERE username=?",
            (username,),
        )
        rows = cursor.fetchall()

    activity_map = {row["date"]: row["completed"] for row in rows}
    days_completed = sum(1 for v in activity_map.values() if v == 1)

    xp = 0
    for day in range(1, num_days + 1):
        date_str = "%04d-%02d-%02d" % (today.year, today.month, day)
        if activity_map.get(date_str):
            xp += 0.25

    return render_template(
        "base.html",
        username=username,
        revealed_at=revealed_at,
        completed=completed,
        current_streak=current_streak,
        best_streak=best_streak,
        xp=xp,
        days_completed=days_completed,
    )


@app.route("/reveal", methods=["POST"])
def reveal():
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401

    username = session["username"]
    now_str = get_utc_now().isoformat()

    import sqlite3
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO activity (username, date, revealed_at, completed) VALUES (?, ?, ?, 0)",
                (username, today_str(), now_str),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass

    return jsonify({"success": True, "revealed_at": now_str})


@app.route("/complete", methods=["POST"])
def complete():
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401

    username = session["username"]
    activity = get_today_activity(username)

    if not activity:
        return jsonify({"error": "Challenge not revealed yet"}), 400

    import datetime
    revealed_at = datetime.datetime.fromisoformat(activity["revealed_at"])
    now = get_utc_now()
    hours_elapsed = (now - revealed_at).total_seconds() / 3600

    if hours_elapsed < 2:
        remaining = 2 - hours_elapsed
        minutes = int(remaining * 60)
        return jsonify({"error": f"Too early. {minutes} minutes remaining."}), 403

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE activity SET completed=1 WHERE username=? AND date=?",
            (username, today_str()),
        )
        conn.commit()

    return jsonify({"success": True})


@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")

def month_index(year, month):
    return year * 12 + (month - 1)

def index_to_month(idx):
    return idx // 12, idx % 12 + 1

@app.route("/challenge")
def challenges():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    current_streak, best_streak = calculate_streaks(username)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, completed FROM activity WHERE username=? ORDER BY date ASC",
            (username,),
        )
        rows = cursor.fetchall()
    
    activity_map = {row["date"]: row["completed"] for row in rows}
    real_today = get_utc_now().date()
    
    if rows:
        first_date = datetime.date.fromisoformat(rows[0]["date"])
        first_year, first_month = first_date.year, first_date.month
    else:
        first_year, first_month = real_today.year, real_today.month    
    
    try:
       view_year = int(request.args.get("year", real_today.year))
       view_month = int(request.args.get("month", real_today.month))     

    except ValueError:
        view_year, view_month = real_today.year, real_today.month
    
    earliest_idx = month_index(first_year, first_month)
    latest_idx = month_index(real_today.year, real_today.month)
    requested_idx = max(earliest_idx, min(month_index(view_year, view_month), latest_idx))
    view_year, view_month = index_to_month(requested_idx)
    
    first_weekday, num_days = calendar.monthrange(view_year, view_month)
    first_weekday = (first_weekday + 1) % 7
    
    prev_year, prev_month = index_to_month(requested_idx - 1)
    next_year, next_month = index_to_month(requested_idx + 1)
    

    return render_template(
        "challenge.html",
        current_streak=current_streak,
        best_streak=best_streak,
        activity_map=activity_map,
        first_weekday=first_weekday,
        num_days=num_days,
        current_year=view_year,
        current_month=view_month,
        can_go_prev=requested_idx > earliest_idx,
        can_go_next=requested_idx < latest_idx,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month
    )


@app.route("/leaderboard")
def leaderboard():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    today = get_utc_now()
    current_year = today.year
    current_month = today.month

    _, num_days = calendar.monthrange(current_year, current_month)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, completed FROM activity WHERE username=?",
            (username,),
        )
        rows = cursor.fetchall()

    activity_map = {row["date"]: row["completed"] for row in rows}

    xp = 0
    for day in range(1, num_days + 1):
        date_str = "%04d-%02d-%02d" % (current_year, current_month, day)
        if activity_map.get(date_str):
            xp += 0.25

    return render_template("leaderboard.html", xp=xp)


@app.route("/profile")
def profile():
    username = session.get("username")
    if not username:
        return redirect("/login")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE username=?", (username,))
        result = cursor.fetchone()

    email = result["email"] if result else None

    return render_template("profile.html", username=username, email=email)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)