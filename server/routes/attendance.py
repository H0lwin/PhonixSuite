# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from utils.auth import require_roles
from models.attendance import ensure_attendance_schema, add_attendance, list_attendance

bp_attendance = Blueprint("attendance", __name__, url_prefix="/api/attendance")


@bp_attendance.post("")
@require_roles("admin", "accountant")
def attendance_add():
    data = request.get_json(silent=True, force=True) or {}
    new_id = add_attendance(data)
    return jsonify({"status": "success", "id": new_id})


@bp_attendance.get("/<int:employee_id>")
@require_roles("admin", "accountant")
def attendance_list(employee_id: int):
    return jsonify({"status": "success", "items": list_attendance(employee_id)})