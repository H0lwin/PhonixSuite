# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, g
from models.loan_buyer import ensure_loan_buyer_schema, create_loan_buyer, update_loan_buyer, list_loan_buyers_for_user, get_loan_buyer, get_loan_buyer_history, delete_loan_buyer
from utils.auth import require_roles, require_auth

bp_loan_buyers = Blueprint("loan_buyers", __name__, url_prefix="/api/loan-buyers")


@bp_loan_buyers.get("")
@require_auth
def lb_list():
    user = g.user
    items = list_loan_buyers_for_user(user_role=user.get("role"), username=user.get("national_id"))
    return jsonify({"status": "success", "items": items})


@bp_loan_buyers.post("")
@require_roles("admin", "broker")
def lb_create():
    user = g.user
    data = request.get_json(silent=True, force=True) or {}
    # Ensure broker username field is set to creator
    if user.get("role") == "broker":
        data["broker"] = user.get("national_id")
    # Set creator full name for display in client
    data["created_by_name"] = user.get("full_name") or user.get("national_id")
    buyer_id = create_loan_buyer(data)
    return jsonify({"status": "success", "id": buyer_id})


@bp_loan_buyers.patch("/<int:buyer_id>")
@require_roles("admin", "broker")
def lb_update(buyer_id: int):
    user = g.user
    data = request.get_json(silent=True, force=True) or {}

    # Enforce ownership for brokers: can only update their own records
    if user.get("role") == "broker":
        from database import get_connection
        conn = get_connection(True)
        cur = conn.cursor()
        cur.execute("SELECT broker FROM loan_buyers WHERE id=%s LIMIT 1", (buyer_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"status": "error", "message": "Not found"}), 404
        if (row[0] or "") != user.get("national_id"):
            return jsonify({"status": "error", "message": "Forbidden: broker cannot modify others' records"}), 403

    update_loan_buyer(buyer_id, data)
    return jsonify({"status": "success"})


@bp_loan_buyers.get("/<int:buyer_id>")
@require_auth
def lb_detail(buyer_id: int):
    item = get_loan_buyer(buyer_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify({"status": "success", "item": item})


@bp_loan_buyers.get("/<int:buyer_id>/history")
@require_auth
def lb_history(buyer_id: int):
    hist = get_loan_buyer_history(buyer_id)
    return jsonify({"status": "success", "items": hist})


@bp_loan_buyers.delete("/<int:buyer_id>")
@require_roles("admin", "broker")
def lb_delete(buyer_id: int):
    user = g.user
    if user.get("role") == "broker":
        from database import get_connection
        conn = get_connection(True)
        cur = conn.cursor()
        cur.execute("SELECT broker FROM loan_buyers WHERE id=%s LIMIT 1", (buyer_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"status": "error", "message": "Not found"}), 404
        if (row[0] or "") != user.get("national_id"):
            return jsonify({"status": "error", "message": "Forbidden: broker cannot delete others' records"}), 403
    delete_loan_buyer(buyer_id)
    return jsonify({"status": "success"})