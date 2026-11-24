
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps
from datetime import date
import os

from database import get_db, initialize_database

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-secret-key")


# -----------------------------
# AUTHENTICATION
# -----------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Login required"}), 401
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


def get_owned_child(child_id):
    conn = get_db()
    child = conn.execute(
        "SELECT * FROM children WHERE id=? AND user_id=?",
        (child_id, session["user_id"])
    ).fetchone()
    conn.close()
    return child


# -----------------------------
# HOME
# -----------------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# -----------------------------
# REGISTER
# -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Caregiver")

        if not fullname or not email or len(password) < 8:
            flash("Complete all fields. Password must be at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if role not in ["Caregiver", "Occupational Therapist", "SPED Teacher"]:
            flash("Invalid account role.", "danger")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            cursor = conn.execute("""
                INSERT INTO users (fullname, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (
                fullname,
                email,
                generate_password_hash(password),
                role
            ))

            user_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO settings (user_id) VALUES (?)",
                (user_id,)
            )

            conn.commit()
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))

        except Exception:
            conn.rollback()
            flash("Email is already registered or registration failed.", "danger")

        finally:
            conn.close()

    return render_template("register.html")


# -----------------------------
# LOGIN
# -----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["fullname"] = user["fullname"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# DASHBOARD
# -----------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()
    user_id = session["user_id"]

    children = conn.execute("""
        SELECT COUNT(*) AS total
        FROM children
        WHERE user_id=?
    """, (user_id,)).fetchone()["total"]

    schedules = conn.execute("""
        SELECT COUNT(*) AS total
        FROM schedules s
        JOIN children c ON s.child_id=c.id
        WHERE c.user_id=?
    """, (user_id,)).fetchone()["total"]

    tasks = conn.execute("""
        SELECT COUNT(*) AS total
        FROM tasks t
        JOIN schedules s ON t.schedule_id=s.id
        JOIN children c ON s.child_id=c.id
        WHERE c.user_id=?
    """, (user_id,)).fetchone()["total"]

    completed = conn.execute("""
        SELECT COUNT(*) AS total
        FROM task_progress p
        JOIN children c ON p.child_id=c.id
        WHERE c.user_id=? AND p.status='Completed'
    """, (user_id,)).fetchone()["total"]

    recent_tasks = conn.execute("""
        SELECT t.*, c.fullname AS child_name
        FROM tasks t
        JOIN schedules s ON t.schedule_id=s.id
        JOIN children c ON s.child_id=c.id
        WHERE c.user_id=?
        ORDER BY t.created_at DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        children=children,
        schedules=schedules,
        tasks=tasks,
        completed=completed,
        recent_tasks=recent_tasks
    )


# -----------------------------
# CHILD PROFILES
# -----------------------------

@app.route("/children")
@login_required
def children():

    conn = get_db()

    records = conn.execute("""
        SELECT * FROM children
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("children.html", children=records)


@app.route("/api/children", methods=["GET", "POST"])
@login_required
def children_api():

    conn = get_db()

    if request.method == "POST":

        data = request.get_json(silent=True) or request.form

        fullname = data.get("fullname", "").strip()

        if not fullname:
            conn.close()
            return jsonify({"error": "Child name is required"}), 400

        try:
            age = int(data.get("age") or 0)
            if age < 0 or age > 120:
                raise ValueError()
        except (ValueError, TypeError):
            conn.close()
            return jsonify({"error": "Invalid age"}), 400

        conn.execute("""
            INSERT INTO children
            (user_id, fullname, age, gender, diagnosis, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            fullname,
            age,
            data.get("gender", ""),
            data.get("diagnosis", ""),
            data.get("notes", "")
        ))

        conn.commit()
        conn.close()

        return jsonify({"message": "Child added successfully"}), 201

    records = conn.execute("""
        SELECT * FROM children WHERE user_id=?
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in records])


@app.route("/api/children/<int:child_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def child_detail_api(child_id):

    child = get_owned_child(child_id)

    if not child:
        return jsonify({"error": "Child not found"}), 404

    if request.method == "GET":
        return jsonify(dict(child))

    conn = get_db()

    if request.method == "PUT":

        data = request.get_json(silent=True) or {}

        fullname = data.get("fullname", child["fullname"]).strip()

        if not fullname:
            conn.close()
            return jsonify({"error": "Name is required"}), 400

        try:
            age = int(data.get("age", child["age"] or 0))
            if age < 0 or age > 120:
                raise ValueError()
        except (ValueError, TypeError):
            conn.close()
            return jsonify({"error": "Invalid age"}), 400

        conn.execute("""
            UPDATE children
            SET fullname=?, age=?, gender=?, diagnosis=?, notes=?
            WHERE id=? AND user_id=?
        """, (
            fullname,
            age,
            data.get("gender", child["gender"]),
            data.get("diagnosis", child["diagnosis"]),
            data.get("notes", child["notes"]),
            child_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return jsonify({"message": "Child updated successfully"})

    conn.execute(
        "DELETE FROM children WHERE id=? AND user_id=?",
        (child_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Child deleted successfully"})


# -----------------------------
# SCHEDULES
# -----------------------------

@app.route("/schedules")
@login_required
def schedules():

    conn = get_db()

    children = conn.execute("""
        SELECT * FROM children
        WHERE user_id=?
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("schedules.html", children=children)


@app.route("/api/schedules", methods=["GET", "POST"])
@login_required
def schedules_api():

    conn = get_db()

    if request.method == "POST":

        data = request.get_json(silent=True) or {}

        child_id = data.get("child_id")
        title = data.get("title", "").strip()
        schedule_date = data.get("schedule_date") or date.today().isoformat()

        if not child_id or not title:
            conn.close()
            return jsonify({"error": "Child and schedule title are required"}), 400

        if not get_owned_child(child_id):
            conn.close()
            return jsonify({"error": "Invalid child"}), 404

        try:
            date.fromisoformat(schedule_date)
        except (ValueError, TypeError):
            conn.close()
            return jsonify({"error": "Invalid schedule date"}), 400

        cursor = conn.execute("""
            INSERT INTO schedules (child_id, title, schedule_date)
            VALUES (?, ?, ?)
        """, (child_id, title, schedule_date))

        schedule_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Schedule created successfully",
            "id": schedule_id
        }), 201

    records = conn.execute("""
        SELECT s.*, c.fullname AS child_name
        FROM schedules s
        JOIN children c ON s.child_id=c.id
        WHERE c.user_id=?
        ORDER BY s.schedule_date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in records])


# -----------------------------
# TASKS
# -----------------------------

@app.route("/api/tasks", methods=["GET", "POST"])
@login_required
def tasks_api():

    conn = get_db()

    if request.method == "POST":

        data = request.get_json(silent=True) or {}

        schedule_id = data.get("schedule_id")
        title = data.get("title", "").strip()

        if not schedule_id or not title:
            conn.close()
            return jsonify({"error": "Schedule and task title are required"}), 400

        schedule = conn.execute("""
            SELECT s.id
            FROM schedules s
            JOIN children c ON s.child_id=c.id
            WHERE s.id=? AND c.user_id=?
        """, (schedule_id, session["user_id"])).fetchone()

        if not schedule:
            conn.close()
            return jsonify({"error": "Schedule not found"}), 404

        cursor = conn.execute("""
            INSERT INTO tasks
            (schedule_id, title, description, start_time,
             end_time, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule_id,
            title,
            data.get("description", ""),
            data.get("start_time", ""),
            data.get("end_time", ""),
            data.get("category", "General"),
            data.get("image_url", "")
        ))

        task_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Task created successfully",
            "id": task_id
        }), 201

    records = conn.execute("""
        SELECT t.*, s.title AS schedule_title, s.child_id
        FROM tasks t
        JOIN schedules s ON t.schedule_id=s.id
        JOIN children c ON s.child_id=c.id
        WHERE c.user_id=?
        ORDER BY t.position, t.id
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in records])


# -----------------------------
# TASK COMPLETION / PROGRESS
# -----------------------------

@app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):

    conn = get_db()

    task = conn.execute("""
        SELECT t.id, s.child_id
        FROM tasks t
        JOIN schedules s ON t.schedule_id=s.id
        JOIN children c ON s.child_id=c.id
        WHERE t.id=? AND c.user_id=?
    """, (task_id, session["user_id"])).fetchone()

    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    conn.execute("""
        UPDATE tasks SET status='Completed'
        WHERE id=?
    """, (task_id,))

    conn.execute("""
        INSERT INTO task_progress (task_id, child_id, status)
        VALUES (?, ?, 'Completed')
    """, (task_id, task["child_id"]))

    conn.commit()
    conn.close()

    return jsonify({"message": "Task marked as completed"})


@app.route("/api/progress")
@login_required
def progress_api():

    conn = get_db()

    records = conn.execute("""
        SELECT
            c.id AS child_id,
            c.fullname AS child_name,
            COUNT(DISTINCT t.id) AS total_tasks,
            COUNT(DISTINCT CASE
                WHEN t.status='Completed' THEN t.id
            END) AS completed_tasks
        FROM children c
        LEFT JOIN schedules s ON s.child_id=c.id
        LEFT JOIN tasks t ON t.schedule_id=s.id
        WHERE c.user_id=?
        GROUP BY c.id
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in records])


@app.route("/progress")
@login_required
def progress():

    return render_template("progress.html")


# -----------------------------
# CHILD VIEW
# -----------------------------

@app.route("/child-view/<int:child_id>")
@login_required
def child_view(child_id):

    child = get_owned_child(child_id)

    if not child:
        flash("Child profile not found.", "danger")
        return redirect(url_for("children"))

    conn = get_db()

    tasks = conn.execute("""
        SELECT t.*, s.title AS schedule_title
        FROM tasks t
        JOIN schedules s ON t.schedule_id=s.id
        WHERE s.child_id=?
        AND s.schedule_date=?
        ORDER BY t.position, t.start_time
    """, (child_id, date.today().isoformat())).fetchall()

    conn.close()

    return render_template(
        "child_view.html",
        child=child,
        tasks=tasks
    )


# -----------------------------
# COMMUNICATION BOARD
# -----------------------------

@app.route("/communication")
@login_required
def communication():

    return render_template("communication.html")


@app.route("/api/communication-cards", methods=["GET", "POST"])
@login_required
def communication_api():

    conn = get_db()

    if request.method == "POST":

        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()

        if not title:
            conn.close()
            return jsonify({"error": "Card title is required"}), 400

        conn.execute("""
            INSERT INTO communication_cards
            (user_id, title, category, image_url, speech_text)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            data.get("category", "General"),
            data.get("image_url", ""),
            data.get("speech_text", title)
        ))

        conn.commit()
        conn.close()

        return jsonify({"message": "Card added successfully"}), 201

    cards = conn.execute("""
        SELECT * FROM communication_cards
        WHERE user_id=?
        ORDER BY category, title
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in cards])


@app.route("/api/communication-cards/<int:card_id>", methods=["DELETE"])
@login_required
def delete_communication_card(card_id):

    conn = get_db()

    cursor = conn.execute("""
        DELETE FROM communication_cards
        WHERE id=? AND user_id=?
    """, (card_id, session["user_id"]))

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if not deleted:
        return jsonify({"error": "Card not found"}), 404

    return jsonify({"message": "Card deleted successfully"})


# -----------------------------
# SETTINGS
# -----------------------------

@app.route("/settings")
@login_required
def settings():

    conn = get_db()

    record = conn.execute("""
        SELECT * FROM settings WHERE user_id=?
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template("settings.html", settings=record)


@app.route("/api/settings", methods=["GET", "PUT"])
@login_required
def settings_api():

    conn = get_db()

    if request.method == "PUT":

        data = request.get_json(silent=True) or {}

        speech = int(bool(data.get("speech_enabled", True)))
        notifications = int(bool(data.get("notification_enabled", True)))
        theme = data.get("theme", "light")

        if theme not in ["light", "dark"]:
            conn.close()
            return jsonify({"error": "Invalid theme"}), 400

        conn.execute("""
            UPDATE settings
            SET speech_enabled=?,
                notification_enabled=?,
                theme=?
            WHERE user_id=?
        """, (
            speech,
            notifications,
            theme,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return jsonify({"message": "Settings saved successfully"})

    record = conn.execute("""
        SELECT * FROM settings WHERE user_id=?
    """, (session["user_id"],)).fetchone()

    conn.close()

    return jsonify(dict(record) if record else {})


# -----------------------------
# ERROR HANDLING
# -----------------------------

@app.errorhandler(404)
def page_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404
    return "Page not found", 404


@app.errorhandler(500)
def server_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return "Internal server error", 500


# -----------------------------
# START APPLICATION
# -----------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
