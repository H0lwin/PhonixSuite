# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from utils.auth import require_roles, require_auth
from models.attendance import (
    add_attendance,
    list_attendance,
    list_attendance_admin,
    check_in as _check_in,
    check_out as _check_out,
    get_daily_status,
    heartbeat as _heartbeat,
)

bp_attendance = Blueprint("attendance", __name__, url_prefix="/api/attendance")


# Backward-compatible add (not recommended for new code)
@bp_attendance.post("")
@require_roles("admin", "accountant")
def attendance_add():
    data = request.get_json(silent=True, force=True) or {}
    new_id = add_attendance(data)
    return jsonify({"status": "success", "id": new_id})


# Employee/Admin: check-in (uses current user by default)
@bp_attendance.post("/check-in")
@require_auth
def attendance_check_in():
    data = request.get_json(silent=True, force=True) or {}
    # Admin/accountant can pass employee_id; others default to self
    emp_id = data.get("employee_id")
    if not emp_id:
        emp_id = (g.user or {}).get("user_id")
    # Optional date override (YYYY-MM-DD)
    day_str = (data.get("date") or "").strip()
    day = None
    if day_str:
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"status": "error", "message": "Invalid date format"}), 400
    sid = _check_in(int(emp_id), day=day)
    # Log activity
    try:
        from models.activity import add_log as _add_log
        _add_log((g.user or {}).get("user_id"), (g.user or {}).get("full_name"), "attendance_check_in", f"employee_id={emp_id}", "success")
    except Exception:
        pass
    # Return up-to-date daily status
    today = day or datetime.now().date()
    daily = get_daily_status(int(emp_id), today)
    return jsonify({"status": "success", "session_id": sid, "daily": daily})


# Employee/Admin: check-out (uses current user by default)
@bp_attendance.post("/check-out")
@require_auth
def attendance_check_out():
    data = request.get_json(silent=True, force=True) or {}
    emp_id = data.get("employee_id")
    if not emp_id:
        emp_id = (g.user or {}).get("user_id")
    day_str = (data.get("date") or "").strip()
    day = None
    if day_str:
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"status": "error", "message": "Invalid date format"}), 400
    sid = _check_out(int(emp_id), day=day)
    # Log activity
    try:
        from models.activity import add_log as _add_log
        _add_log((g.user or {}).get("user_id"), (g.user or {}).get("full_name"), "attendance_check_out", f"employee_id={emp_id}", "success")
    except Exception:
        pass
    today = day or datetime.now().date()
    daily = get_daily_status(int(emp_id), today)
    return jsonify({"status": "success", "session_id": sid, "daily": daily})


# Admin filtered list
@bp_attendance.get("/admin")
@require_roles("admin", "accountant", "secretary")
def attendance_admin_list():
    emp_id = request.args.get("employee_id", type=int)
    df = request.args.get("date_from", type=str)
    dt = request.args.get("date_to", type=str)
    date_from = date_to = None
    try:
        if df:
            date_from = datetime.strptime(df, "%Y-%m-%d").date()
        if dt:
            date_to = datetime.strptime(dt, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"status": "error", "message": "Invalid date format"}), 400
    items = list_attendance_admin(emp_id, date_from, date_to)
    # Diagnostic logging for troubleshooting empty attendance table in UI
    try:
        import logging
        logging.getLogger("routes.attendance").info(
            "/api/attendance/admin employee_id=%s from=%s to=%s count=%s",
            emp_id, date_from, date_to, len(items),
        )
    except Exception:
        pass
    return jsonify({"status": "success", "count": len(items), "items": items})


# Heartbeat: keeps today's session alive and crash-safe
@bp_attendance.post("/heartbeat")
@require_auth
def attendance_heartbeat():
    from flask import g
    emp_id = (g.user or {}).get("user_id")
    if not emp_id:
        return jsonify({"status": "error", "message": "No user"}), 400
    try:
        _heartbeat(int(emp_id))
        return jsonify({"status": "success"})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# Per-employee daily summary
@bp_attendance.get("/<int:employee_id>")
@require_roles("admin", "accountant", "secretary")
def attendance_list(employee_id: int):
    return jsonify({"status": "success", "items": list_attendance(employee_id)})