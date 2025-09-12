# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from models.creditor import (
    ensure_creditor_schema,
    list_creditors,
    add_installment,
    create_creditor,
    update_creditor,
    delete_creditor,
    get_creditor,
    settle_creditor,
)
from utils.auth import require_roles, require_auth

bp_creditors = Blueprint("creditors", __name__, url_prefix="/api/creditors")


@bp_creditors.get("")
@require_roles("admin")
def creditors_list():
    status = request.args.get("status")
    status = status.lower() if status else None
    if status not in (None, "settled", "unsettled"):
        return jsonify({"status": "error", "message": "invalid status"}), 400
    items = list_creditors(status)
    try:
        import logging
        logging.getLogger(__name__).info("/api/creditors status=%s count=%s", status, len(items))
    except Exception:
        pass
    return jsonify({"status": "success", "items": items})


@bp_creditors.post("")
@require_roles("admin")
def creditors_create():
    data = request.get_json(silent=True, force=True) or {}
    full_name = (data.get("full_name") or "").strip()
    try:
        amount = float(data.get("amount") or 0)
    except Exception:
        amount = 0.0
    description = (data.get("description") or "").strip()
    if not full_name:
        return jsonify({"status": "error", "message": "full_name is required"}), 400
    new_id = create_creditor(full_name, amount, description)
    return jsonify({"status": "success", "id": new_id})


@bp_creditors.get("/<int:creditor_id>")
@require_roles("admin")
def creditors_get(creditor_id: int):
    item = get_creditor(creditor_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify({"status": "success", "item": item})


@bp_creditors.patch("/<int:creditor_id>")
@require_roles("admin")
def creditors_update(creditor_id: int):
    data = request.get_json(silent=True, force=True) or {}
    update_creditor(creditor_id, data)
    return jsonify({"status": "success"})


@bp_creditors.delete("/<int:creditor_id>")
@require_roles("admin")
def creditors_delete(creditor_id: int):
    delete_creditor(creditor_id)
    return jsonify({"status": "success"})


@bp_creditors.post("/<int:creditor_id>/installments")
@require_roles("admin")
def creditors_add_installment(creditor_id: int):
    data = request.get_json(silent=True, force=True) or {}
    add_installment(creditor_id, data.get("amount", 0), data.get("date"), data.get("notes"))
    return jsonify({"status": "success"})

@bp_creditors.get("/<int:creditor_id>/installments")
@require_roles("admin")
def creditors_list_installments(creditor_id: int):
    from models.creditor import get_creditor
    item = get_creditor(creditor_id) or {"installments": [], "paid_amount": 0, "remaining_amount": 0, "amount": 0, "settlement_status": "unsettled"}
    return jsonify({
        "status": "success",
        "installments": item.get("installments", []),
        "paid_amount": item.get("paid_amount", 0),
        "remaining_amount": item.get("remaining_amount", 0),
        "total_amount": item.get("amount", 0),
        "settlement_status": item.get("settlement_status", "unsettled")
    })

@bp_creditors.patch("/<int:creditor_id>/installments/<int:inst_id>")
@require_roles("admin")
def creditors_update_installment(creditor_id: int, inst_id: int):
    data = request.get_json(silent=True, force=True) or {}
    from database import get_connection
    from models.creditor import _recalc_status as recalc
    conn = get_connection(True); cur = conn.cursor()
    try:
        cur.execute("UPDATE creditor_installments SET amount=%s, pay_date=%s, notes=%s WHERE id=%s AND creditor_id=%s", (data.get("amount", 0), data.get("date"), data.get("notes"), inst_id, creditor_id))
        # Recalculate status in the same connection
        recalc(conn, creditor_id)
        conn.commit()
        return jsonify({"status": "success"})
    finally:
        cur.close(); conn.close()

@bp_creditors.delete("/<int:creditor_id>/installments/<int:inst_id>")
@require_roles("admin")
def creditors_delete_installment(creditor_id: int, inst_id: int):
    from database import get_connection
    from models.creditor import _recalc_status as recalc
    conn = get_connection(True); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM creditor_installments WHERE id=%s AND creditor_id=%s", (inst_id, creditor_id))
        # Recalculate status in the same connection
        recalc(conn, creditor_id)
        conn.commit()
        return jsonify({"status": "success"})
    finally:
        cur.close(); conn.close()


@bp_creditors.post("/<int:creditor_id>/settle")
@require_roles("admin")
def creditors_settle(creditor_id: int):
    data = request.get_json(silent=True, force=True) or {}
    settle_creditor(creditor_id, data.get("date"), data.get("notes"))
    return jsonify({"status": "success"})