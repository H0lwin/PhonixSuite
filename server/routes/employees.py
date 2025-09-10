# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
# Use module-local import so server/app.py can run as a script
from models.employee import (
    ensure_employee_schema,
    create_employee,
    get_departments,
    get_branches,
)
from utils.auth import require_roles

bp_employees = Blueprint("employees", __name__, url_prefix="/api/employees")


# Schema is ensured during application startup in server/app.py

@bp_employees.get("/meta")
@require_roles("admin")
def employees_meta():
    """Return departments and branches for dropdowns."""
    deps = get_departments()
    brs = get_branches()
    return jsonify({"departments": deps, "branches": brs})


@bp_employees.get("")
@require_roles("admin")
def employees_list():
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    # Include department_id and branch_id for client-side filtering
    cur.execute("SELECT id, full_name, national_id, role, status, department_id, branch_id FROM employees ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    items = [
        {
            "id": r[0],
            "full_name": r[1],
            "national_id": r[2],
            "role": r[3],
            "status": r[4],
            "department_id": r[5],
            "branch_id": r[6],
        }
        for r in rows
    ]
    return jsonify({"status": "success", "items": items})


@bp_employees.post("")
@require_roles("admin")
def employees_create():
    data = request.get_json(silent=True, force=True) or {}
    required = ["full_name", "national_id", "password", "role", "status"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"status": "error", "message": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        new_id = create_employee(data)
        return jsonify({"status": "success", "id": new_id})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@bp_employees.get("/<int:emp_id>")
@require_roles("admin")
def employees_get(emp_id: int):
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    # Return complete details for view dialog
    cur.execute(
        """
        SELECT id, full_name, national_id, role, status, department_id, branch_id, phone, address, monthly_salary
        FROM employees WHERE id=%s
        """,
        (emp_id,)
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify({
        "status": "success",
        "item": {
            "id": row[0],
            "full_name": row[1],
            "national_id": row[2],
            "role": row[3],
            "status": row[4],
            "department_id": row[5],
            "branch_id": row[6],
            "phone": row[7],
            "address": row[8],
            "monthly_salary": float(row[9]) if row[9] is not None else 0,
        }
    })


@bp_employees.patch("/<int:emp_id>")
@require_roles("admin")
def employees_update(emp_id: int):
    data = request.get_json(silent=True, force=True) or {}
    # Hash password if provided
    if "password" in data and data["password"]:
        try:
            import bcrypt
            data["password"] = bcrypt.hashpw(str(data["password"]).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except Exception:
            # leave as-is if bcrypt not available
            pass

    allowed = ["full_name", "national_id", "password", "role", "status"]
    fields, values = [], []
    for k in allowed:
        if k in data:
            fields.append(f"{k}=%s"); values.append(data[k])
    if not fields:
        return jsonify({"status": "error", "message": "No fields"}), 400
    values.append(emp_id)
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(f"UPDATE employees SET {', '.join(fields)} WHERE id=%s", tuple(values))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "success"})


@bp_employees.delete("/<int:emp_id>")
@require_roles("admin")
def employees_delete(emp_id: int):
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE id=%s", (emp_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "success"})
