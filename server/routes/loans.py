# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, g
from models.loan import ensure_loan_schema, create_loan, list_loans, get_loan, update_loan, delete_loan
from models.creditor import create_creditor
from utils.auth import require_roles, require_auth

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
    pre = get_loan(loan_id)
    if not pre:
        return jsonify({"status": "error", "message": "Not found"}), 404

    update_loan(loan_id, data)

    # If status changed to purchased, create creditor automatically
    post = get_loan(loan_id)
    if pre and pre.get("loan_status") != "purchased" and post.get("loan_status") == "purchased":
        full_name = post.get("owner_full_name")
        amount = post.get("purchase_rate") or 0
        description = f"loan_id={loan_id}, rate={post.get('purchase_rate')}, bank={post.get('bank_name')}"
        create_creditor(full_name, amount, description)
    return jsonify({"status": "success"})


@bp_loans.delete("/<int:loan_id>")
@require_roles("admin")
def loans_delete(loan_id: int):
    item = get_loan(loan_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    delete_loan(loan_id)
    return jsonify({"status": "success"})