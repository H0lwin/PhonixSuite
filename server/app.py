# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import os
import getpass
import argparse
import logging
from logging.handlers import RotatingFileHandler

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Local imports (module-local, not package-relative to allow running as a script)
from database import get_connection
from models.employee import (
    ensure_employee_schema,
    get_employee_by_national_id,
)
from models.loan import ensure_loan_schema
from models.loan_buyer import ensure_loan_buyer_schema
from models.creditor import ensure_creditor_schema
from models.finance import ensure_finance_schema
from routes.employees import bp_employees
from routes.loans import bp_loans
from routes.loan_buyers import bp_loan_buyers
from routes.creditors import bp_creditors
from routes.finance import bp_finance
from routes.attendance import bp_attendance

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False


# ----- Database bootstrap -----

def ensure_database_exists():
    dbname = os.getenv("DB_NAME", "myapp")
    host = os.getenv("DB_HOST", "127.0.0.1")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "1234")
    port = int(os.getenv("DB_PORT", "3306"))

    # Connect without DB selected
    import mysql.connector

    conn = mysql.connector.connect(host=host, user=user, password=password, port=port, autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (dbname,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f"CREATE DATABASE `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    cur.close()
    conn.close()


def ensure_admin_wizard(force: bool = False):
    """CLI wizard to create an admin employee if none exists."""
    # Ensure schema first
    ensure_employee_schema()

    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees WHERE role='admin'")
    admin_count = cur.fetchone()[0]
    if not force and admin_count > 0:
        cur.close()
        conn.close()
        return

    print("There is no admin user. Please create an admin employee.")
    while True:
        full_name = input("Admin Full Name: ").strip()
        if not full_name:
            print("Full name cannot be empty.")
            continue
        national_id = input("Admin National ID (10 digits): ").strip()
        if not national_id or not national_id.isdigit() or len(national_id) != 10:
            print("National ID must be 10 digits.")
            continue
        # Check uniqueness
        cur.execute("SELECT COUNT(*) FROM employees WHERE national_id=%s", (national_id,))
        if cur.fetchone()[0] > 0:
            print("This national ID already exists. Choose another one.")
            continue
        password = getpass.getpass("Password: ").strip()
        repeat = getpass.getpass("Repeat password: ").strip()
        if not password:
            print("Password cannot be empty.")
            continue
        if password != repeat:
            print("The password and its repetition are not the same.")
            continue

        # Hash password with bcrypt
        try:
            import bcrypt
            hashed_pwd = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except Exception:
            hashed_pwd = password

        cur.execute(
            """
            INSERT INTO employees (full_name, national_id, password, role, status)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (full_name, national_id, hashed_pwd, "admin", "active"),
        )
        conn.commit()
        print("Administrator employee created successfully.")
        break

    cur.close()
    conn.close()


# ----- Routes -----

from utils.auth import issue_token, revoke_token, require_auth


@app.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True, force=True) or {}
    national_id = str(data.get("national_id", "")).strip()
    password = str(data.get("password", "")).strip()
    if not national_id or not password:
        return jsonify({"status": "error", "message": "national_id and password are required"}), 400

    try:
        user = get_employee_by_national_id(national_id)
        if not user or user.get("status") != "active":
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        # Verify password using bcrypt if possible
        valid = False
        try:
            import bcrypt
            stored = (user.get("password") or "").encode("utf-8")
            valid = bcrypt.checkpw(password.encode("utf-8"), stored)
        except Exception:
            # Fallback to plain comparison if bcrypt not available
            valid = user.get("password") == password

        if not valid:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        # Map role for RBAC; accept multiple roles such as admin/secretary/broker/accountant
        role = user.get("role") or "user"
        token = issue_token(user)
        return jsonify({
            "status": "success",
            "role": role,
            "display_name": user.get("full_name"),
            "token": token,
        })
    except Exception as exc:
        app.logger.exception("Login error: %s", exc)
        return jsonify({"status": "error", "message": "Database error"}), 500


@app.post("/api/auth/logout")
@require_auth
def api_logout():
    # Revoke token if provided
    token = request.headers.get("X-Auth-Token", "")
    revoke_token(token)
    return jsonify({"status": "success"})


# Register blueprints
app.register_blueprint(bp_employees)
app.register_blueprint(bp_loans)
app.register_blueprint(bp_loan_buyers)
app.register_blueprint(bp_creditors)
app.register_blueprint(bp_finance)
app.register_blueprint(bp_attendance)


# ----- Bootstrapping and logging -----

def start_server():
    ensure_database_exists()
    # Ensure all module schemas
    ensure_employee_schema()
    ensure_loan_schema()
    ensure_loan_buyer_schema()
    ensure_creditor_schema()
    ensure_finance_schema()
    from models.attendance import ensure_attendance_schema
    ensure_attendance_schema()
    ensure_admin_wizard()


def run_create_admin(force: bool = False):
    ensure_database_exists()
    ensure_employee_schema()
    ensure_admin_wizard(force=force)


def migrate_passwords():
    """One-time migration helper: hash plain-text passwords with bcrypt if not already hashed."""
    try:
        import bcrypt  # noqa: F401
    except Exception:
        print("bcrypt is not installed. Please install requirements first.")
        return
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("SELECT id, password FROM employees")
    rows = cur.fetchall()
    updated = 0
    for emp_id, pwd in rows:
        pwd = pwd or ""
        if pwd.startswith("$2a$") or pwd.startswith("$2b$") or pwd.startswith("$2y$"):
            continue  # looks like bcrypt
        import bcrypt
        hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("UPDATE employees SET password=%s WHERE id=%s", (hashed, emp_id))
        updated += 1
    if updated:
        conn.commit()
    cur.close(); conn.close()
    print(f"Password migration completed. Updated {updated} record(s).")


def configure_logging():
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "server.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    werk = logging.getLogger("werkzeug")
    werk.setLevel(logging.INFO)
    werk.addHandler(handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run server and admin tools")
    parser.add_argument("--create-admin", action="store_true", help="Run admin wizard")
    parser.add_argument("--force", action="store_true", help="Always run admin wizard")
    parser.add_argument("--migrate-passwords", action="store_true", help="Hash existing plain-text passwords with bcrypt")
    args = parser.parse_args()

    configure_logging()
    if args.create_admin:
        run_create_admin(force=args.force)
    elif args.migrate_passwords:
        migrate_passwords()
    else:
        start_server()
        app.run(host="127.0.0.1", port=5000, debug=True)
