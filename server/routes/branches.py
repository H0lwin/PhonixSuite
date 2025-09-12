# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from utils.auth import require_roles
from models.branch import ensure_branch_schema, list_branches_with_counts, create_branch, delete_branch, get_branch_employees
from models.employee import ensure_employee_schema

bp_branches = Blueprint("branches", __name__, url_prefix="/api/branches")

# Ensure schema on import (app.startup also ensures)
ensure_employee_schema()
ensure_branch_schema()


@bp_branches.get("")
@require_roles("admin")
def list_branches():
    items = list_branches_with_counts()
    return jsonify({"status": "success", "items": items})


@bp_branches.post("")
@require_roles("admin")
def add_branch():
    data = request.get_json(silent=True, force=True) or {}
    name = str(data.get("name", "")).strip()
    location = str(data.get("location", "")).strip() or None
    manager_id = data.get("manager_id")
    if not name:
        return jsonify({"status": "error", "message": "Branch name is required"}), 400
    try:
        bid = create_branch(name, location, manager_id)
        return jsonify({"status": "success", "id": bid})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@bp_branches.delete("/<int:branch_id>")
@require_roles("admin")
def remove_branch(branch_id: int):
    try:
        delete_branch(branch_id)
        return jsonify({"status": "success"})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@bp_branches.get("/<int:branch_id>/employees")
@require_roles("admin")
def branch_employees(branch_id: int):
    try:
        items = get_branch_employees(branch_id)
        return jsonify({"status": "success", "items": items})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400