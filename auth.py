# auth.py
import sqlite3

from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from models import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password FROM users WHERE username=?", (username,)
            )
            result = cursor.fetchone()

        if result and check_password_hash(result["password"], password):
            session["username"] = username
            return redirect("/base")
        return "Invalid username or password"

    return render_template("login.html")


@auth_bp.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form.get("email")
        hashed_password = generate_password_hash(password)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                    (username, hashed_password, email),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            return "Username is already taken."

        session["username"] = username
        return redirect("/base")

    return render_template("register.html")

# Add this route to your auth.py file

# Place this inside auth.py

@auth_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    # Require authentication
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        username = session["username"]

        # Check if new passwords match
        if new_password != confirm_password:
            return render_template(
                "change_password.html", 
                error="New passwords do not match."
            )

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username=?", (username,))
            result = cursor.fetchone()

            # Verify current password
            if result and check_password_hash(result["password"], old_password):
                hashed_new = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET password=? WHERE username=?",
                    (hashed_new, username),
                )
                conn.commit()
                return redirect("/profile")
            else:
                return render_template(
                    "change_password.html", 
                    error="Incorrect current password."
                )

    return render_template("change_password.html")
@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect("/")