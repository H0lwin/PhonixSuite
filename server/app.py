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
from routes.branches import bp_branches
from models.activity import ensure_activity_schema, add_log, list_recent, cleanup_old_logs
from routes.activity import bp_activity
from models.auth_token import ensure_auth_token_schema, cleanup_expired_tokens

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False

# Global activity logging for mutating requests
@app.before_request
def _capture_activity_start():
    from flask import g, request
    g._log_mutation = request.method in ("POST", "PUT", "PATCH", "DELETE")
    if g._log_mutation:
        try:
            g._req_body_preview = (request.get_data(as_text=True) or "")[:500]
        except Exception:
            g._req_body_preview = None


@app.after_request
def _log_activity_after(response):
    from flask import g, request
    try:
        if getattr(g, "_log_mutation", False):
            user = getattr(g, "user", None)
            uid = (user or {}).get("user_id")
            uname = (user or {}).get("full_name") or (user or {}).get("national_id")
            status = "success" if (response.status_code < 400) else "error"
            action = f"{request.method} {request.path}"
            details = g._req_body_preview or ""
            try:
                add_log(uid, uname, action, details, status)
            except Exception:
                pass
    except Exception:
        pass
    return response


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
    """Create an admin if none exists.
    - If ADMIN_WIZARD_MODE=interactive and TTY available → prompt the user.
    - Otherwise, create a temporary admin with env/defaults and log the credentials.
    """
    import sys, os
    # Ensure schema first
    ensure_employee_schema()

    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees WHERE role='admin'")
    admin_count = cur.fetchone()[0]
    if not force and admin_count > 0:
        cur.close(); conn.close(); return

    # Decide mode
    mode = (os.getenv("ADMIN_WIZARD_MODE", "auto") or "auto").lower().strip()
    try:
        is_tty = sys.stdin is not None and sys.stdin.isatty()
    except Exception:
        is_tty = False

    should_prompt = (mode == "interactive" and is_tty)

    if should_prompt:
        print("There is no admin user. Please create an admin employee.")
        while True:
            full_name = input("Admin Full Name: ").strip()
            if not full_name:
                print("Full name cannot be empty."); continue
            national_id = input("Admin National ID (10 digits): ").strip()
            if not national_id or not national_id.isdigit() or len(national_id) != 10:
                print("National ID must be 10 digits."); continue
            # Check uniqueness
            cur.execute("SELECT COUNT(*) FROM employees WHERE national_id=%s", (national_id,))
            if cur.fetchone()[0] > 0:
                print("This national ID already exists. Choose another one."); continue
            password = getpass.getpass("Password: ").strip()
            repeat = getpass.getpass("Repeat password: ").strip()
            if not password:
                print("Password cannot be empty."); continue
            if password != repeat:
                print("The password and its repetition are not the same."); continue

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
            cur.close(); conn.close(); return

    # Non-interactive path: create a temporary admin and log credentials
    full_name = os.getenv("DEFAULT_ADMIN_NAME", "Admin User")
    national_id = os.getenv("DEFAULT_ADMIN_NID", "9999999999")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    if not password:
        # Generate a simple random password
        try:
            import secrets, string
            alph = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alph) for _ in range(12))
        except Exception:
            password = "ChangeMe123"

    # Ensure unique national_id (increment last digit if needed)
    for _ in range(5):
        cur.execute("SELECT COUNT(*) FROM employees WHERE national_id=%s", (national_id,))
        if cur.fetchone()[0] == 0:
            break
        # bump last digit (wrap to 0)
        national_id = national_id[:-1] + str((int(national_id[-1]) + 1) % 10)

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
    try:
        msg = f"Temporary admin created (non-interactive): name='{full_name}', national_id='{national_id}', password='{password}'"
        print(msg)
        try:
            app.logger.warning(msg)
        except Exception:
            pass
    except Exception:
        pass
    cur.close(); conn.close()


# ----- Routes -----

from utils.auth import issue_token, revoke_token, require_auth, require_admin

# Public health-check (no auth)
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


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
            add_log(None, national_id, "login", "invalid user or inactive", "failure")
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
            add_log(user.get("id"), user.get("full_name"), "login", "wrong password", "failure")
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        # Map role for RBAC; accept multiple roles such as admin/secretary/broker/accountant
        role = user.get("role") or "user"
        token = issue_token(user)
        add_log(user.get("id"), user.get("full_name"), "login", f"role={role}", "success")
        return jsonify({
            "status": "success",
            "role": role,
            "display_name": user.get("full_name"),
            "token": token,
        })
    except Exception as exc:
        app.logger.exception("Login error: %s", exc)
        add_log(None, national_id, "login", "db error", "error")
        return jsonify({"status": "error", "message": "Database error"}), 500


@app.post("/api/auth/logout")
@require_auth
def api_logout():
    # Revoke token if provided
    token = request.headers.get("X-Auth-Token", "")
    revoke_token(token)
    return jsonify({"status": "success"})


@app.get("/api/admin/active-users")
@require_admin
def api_active_users():
    """Return count of currently active sessions (non-expired tokens)."""
    try:
        from models.auth_token import cleanup_expired_tokens
        from database import get_connection
        # Clean up first (non-blocking if fails)
        try:
            cleanup_expired_tokens()
        except Exception:
            pass
        conn = get_connection(True)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM auth_tokens WHERE expires_at > CURRENT_TIMESTAMP")
        count = int(cur.fetchone()[0] or 0)
        cur.close(); conn.close()
        return jsonify({"status": "success", "count": count})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# Register blueprints
app.register_blueprint(bp_employees)
app.register_blueprint(bp_loans)
app.register_blueprint(bp_loan_buyers)
app.register_blueprint(bp_creditors)
app.register_blueprint(bp_finance)
app.register_blueprint(bp_attendance)
app.register_blueprint(bp_branches)
app.register_blueprint(bp_activity)


# Client-side logs receiver
@app.post("/api/client-logs")
def api_client_logs():
    try:
        data = request.get_json(silent=True, force=True) or {}
        level = str(data.get("level", "INFO")).upper()
        message = str(data.get("message", "")).strip()
        logger_name = str(data.get("logger", "client")).strip() or "client"
        # Map level
        lvl = getattr(logging, level, logging.INFO)
        logging.getLogger(logger_name).log(lvl, "[client] %s", message)
        return jsonify({"status": "success"})
    except Exception as exc:
        app.logger.exception("client log error: %s", exc)
        return jsonify({"status": "error"}), 500


# ----- Bootstrapping and logging -----

def start_server(skip_admin_wizard: bool = True):
    """Initialize database and schemas. In production, skip interactive admin wizard by default."""
    ensure_database_exists()
    # Ensure all module schemas
    ensure_employee_schema()
    ensure_auth_token_schema()
    ensure_loan_schema()
    ensure_loan_buyer_schema()
    ensure_creditor_schema()
    ensure_finance_schema()
    from models.attendance import ensure_attendance_schema
    ensure_attendance_schema()
    ensure_activity_schema()
    # Cleanup logs and expired tokens
    cleanup_old_logs()
    try:
        removed = cleanup_expired_tokens()
        if removed:
            app.logger.info("Auth tokens cleanup: removed %s expired tokens", removed)
    except Exception:
        pass
    # Avoid interactive prompts in production unless explicitly requested
    if not skip_admin_wizard:
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


def backfill_creditors():
    """Backfill creditors for already purchased loans that lack a creditor row."""
    ensure_database_exists()
    ensure_loan_schema()
    ensure_creditor_schema()
    from models.creditor import create_creditor
    from database import get_connection

    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("SELECT id, owner_full_name, purchase_rate, bank_name, owner_phone FROM loans WHERE loan_status='purchased'")
    rows = cur.fetchall()
    created = 0; skipped = 0
    for loan_id, full_name, rate, bank_name, owner_phone in rows:
        cur2 = conn.cursor()
        cur2.execute("SELECT COUNT(*) FROM creditors WHERE loan_id=%s", (loan_id,))
        exists = int(cur2.fetchone()[0] or 0)
        cur2.close()
        if exists:
            skipped += 1
            continue
        try:
            amount = float(rate or 0)
        except Exception:
            amount = 0.0
        desc = f"loan_id={loan_id}, rate={rate}, bank={bank_name}"
        create_creditor((full_name or '').strip(), amount, desc, loan_id=loan_id, loan_rate=rate, bank_name=bank_name, owner_phone=owner_phone)
        created += 1
    cur.close(); conn.close()
    print(f"Backfill creditors completed. Created={created}, Skipped={skipped}")


def configure_logging():
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "server.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # App logger
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # Werkzeug access logger
    werk = logging.getLogger("werkzeug")
    werk.setLevel(logging.INFO)
    werk.addHandler(handler)

    # Root logger (ensure any plain logging.* also goes into file)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


# Global JSON error handler for unexpected exceptions
@app.errorhandler(Exception)
def _json_error_handler(exc):
    try:
        app.logger.exception("Unhandled error: %s", exc)
    except Exception:
        pass
    return jsonify({"status": "error", "message": "Internal server error"}), 500


def backfill_creditor_metadata():
    """Populate missing creditor metadata (loan_rate, bank_name, owner_phone) for rows with loan_id.

    Joins creditors with loans and updates NULL fields only.
    """
    ensure_database_exists()
    ensure_loan_schema()
    ensure_creditor_schema()
    from database import get_connection

    conn = get_connection(True)
    cur = conn.cursor()
    # Find creditors with loan_id where any metadata is NULL
    cur.execute(
        """
        SELECT c.id, c.loan_id, l.purchase_rate, l.bank_name, l.owner_phone
        FROM creditors c
        JOIN loans l ON l.id = c.loan_id
        WHERE c.loan_id IS NOT NULL AND (c.loan_rate IS NULL OR c.bank_name IS NULL OR c.owner_phone IS NULL)
        """
    )
    rows = cur.fetchall()
    updated = 0
    for cid, loan_id, rate, bank, phone in rows:
        # Build dynamic update only for NULLs
        fields = []
        values = []
        if rate is not None:
            fields.append("loan_rate=%s"); values.append(rate)
        if bank is not None:
            fields.append("bank_name=%s"); values.append(bank)
        if phone is not None:
            fields.append("owner_phone=%s"); values.append(phone)
        if not fields:
            continue
        values.append(cid)
        cur2 = conn.cursor()
        cur2.execute(f"UPDATE creditors SET {', '.join(fields)} WHERE id=%s", tuple(values))
        cur2.close()
        updated += 1
    if updated:
        conn.commit()
    cur.close(); conn.close()
    print(f"Backfill creditor metadata completed. Updated {updated} record(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run server and admin tools")
    parser.add_argument("--create-admin", action="store_true", help="Run admin wizard")
    parser.add_argument("--force", action="store_true", help="Always run admin wizard")
    parser.add_argument("--migrate-passwords", action="store_true", help="Hash existing plain-text passwords with bcrypt")
    parser.add_argument("--backfill-creditors", action="store_true", help="Create creditors for already purchased loans that don't have creditors")
    parser.add_argument("--backfill-creditor-metadata", action="store_true", help="Populate missing creditor metadata from related loans")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")))
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (development only)")
    args = parser.parse_args()

    configure_logging()
    if args.create_admin:
        run_create_admin(force=args.force)
    elif args.migrate_passwords:
        migrate_passwords()
    elif args.backfill_creditors:
        backfill_creditors()
    elif args.backfill_creditor_metadata:
        backfill_creditor_metadata()
    else:
        # Development runner only; do not use in production
        start_server(skip_admin_wizard=True)
        app.run(host=args.host, port=args.port, debug=args.debug)
