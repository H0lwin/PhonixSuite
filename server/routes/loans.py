# -*- coding: utf-8 -*-
import logging
from flask import Blueprint, request, jsonify, g, current_app
from models.loan import ensure_loan_schema, create_loan, list_loans, get_loan, update_loan, delete_loan
from models.creditor import create_creditor
from utils.auth import require_roles, require_auth

log = logging.getLogger(__name__)

bp_loans = Blueprint("loans", __name__, url_prefix="/api/loans")

# Schema ensured in app startup


@bp_loans.get("")
@require_auth
def loans_list():
    user = g.user
    items = list_loans()
    # If secretary, restrict fields
    if user.get("role") == "secretary":
        allowed = {"id","bank_name","loan_type","duration","amount","loan_status"}
        items = [{k: v for k, v in it.items() if k in allowed} for it in items]
    return jsonify({"status": "success", "items": items})


@bp_loans.post("")
@require_roles("admin")
def loans_create():
    data = request.get_json(silent=True, force=True) or {}
    new_id = create_loan(data)
    return jsonify({"status": "success", "id": new_id})


@bp_loans.get("/<int:loan_id>")
@require_auth
def loans_get(loan_id: int):
    user = g.user
    item = get_loan(loan_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    if user.get("role") == "secretary":
        allowed = {"id","bank_name","loan_type","duration","amount","loan_status"}
        item = {k: v for k, v in item.items() if k in allowed}
    return jsonify({"status": "success", "item": item})


@bp_loans.patch("/<int:loan_id>")
@require_roles("admin")
def loans_update(loan_id: int):
    data = request.get_json(silent=True, force=True) or {}
    # Log via both Flask app logger and module logger (root handler also attached)
    role = None
    try:
        role = getattr(g, 'user', {}) and getattr(g.user, 'get', lambda *_: None)('role')
    except Exception:
        role = None
    current_app.logger.info("PATCH /api/loans/%s payload=%s (user_role=%s)", loan_id, data, role)
    log.info("PATCH /api/loans/%s payload=%s (user_role=%s)", loan_id, data, role)
    pre = get_loan(loan_id)
    if not pre:
        current_app.logger.warning("Loan %s not found for PATCH", loan_id)
        return jsonify({"status": "error", "message": "Not found"}), 404

    current_app.logger.info("Loan %s BEFORE: status=%s, owner=%s, purchase_rate=%s", loan_id, pre.get("loan_status"), pre.get("owner_full_name"), pre.get("purchase_rate"))
    update_loan(loan_id, data)

    # If status changed to purchased, create creditor automatically
    post = get_loan(loan_id)
    pre_status = (pre or {}).get("loan_status")
    post_status = (post or {}).get("loan_status")
    current_app.logger.info("Loan %s AFTER: status=%s, owner=%s, purchase_rate=%s", loan_id, post.get("loan_status"), post.get("owner_full_name"), post.get("purchase_rate"))
    current_app.logger.info("Loan %s status change: %s -> %s", loan_id, pre_status, post_status)
    if pre and pre_status != "purchased" and post_status == "purchased":
        full_name = (post.get("owner_full_name") or "").strip()
        try:
            amount = float(post.get("purchase_rate") or 0)
        except Exception as e:
            current_app.logger.exception("Loan %s invalid purchase_rate: %s", loan_id, e)
            amount = 0.0
        description = f"loan_id={loan_id}, rate={post.get('purchase_rate')}, bank={post.get('bank_name')}"
        if not full_name:
            current_app.logger.warning("Loan %s owner_full_name is empty; creating creditor with empty name.", loan_id)
        if amount <= 0:
            current_app.logger.warning("Loan %s purchase_rate is %s; creditor will be created with non-positive amount.", loan_id, amount)
        # Avoid duplicate creditor for same loan: check if exists by loan_id
        from database import get_connection
        conn = get_connection(True); cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM creditors WHERE loan_id=%s", (loan_id,))
            exists = int(cur.fetchone()[0] or 0)
        except Exception as e:
            current_app.logger.exception("Creditor existence check failed for loan %s: %s", loan_id, e)
            exists = 0
        finally:
            cur.close(); conn.close()
        if exists == 0:
            try:
                cid = create_creditor(full_name, amount, description, loan_id=loan_id)
                current_app.logger.info("Created creditor id=%s for loan %s (name=%s, amount=%s)", cid, loan_id, full_name, amount)
            except Exception as e:
                current_app.logger.exception("Creating creditor failed for loan %s: %s", loan_id, e)
        else:
            current_app.logger.info("Creditor already exists for loan %s; skipping creation", loan_id)
    else:
        current_app.logger.info("No creditor creation condition met for loan %s (pre_status=%s, post_status=%s)", loan_id, pre_status, post_status)
    return jsonify({"status": "success"})


@bp_loans.delete("/<int:loan_id>")
@require_roles("admin")
def loans_delete(loan_id: int):
    item = get_loan(loan_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    delete_loan(loan_id)
    return jsonify({"status": "success"})