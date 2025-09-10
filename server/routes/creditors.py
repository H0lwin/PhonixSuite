# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from models.creditor import ensure_creditor_schema, list_creditors, add_installment
from utils.auth import require_roles, require_auth

bp_creditors = Blueprint("creditors", __name__, url_prefix="/api/creditors")


@bp_creditors.get("")
@require_roles("admin")
def creditors_list():
    return jsonify({"status": "success", "items": list_creditors()})


@bp_creditors.post("/<int:creditor_id>/installments")
@require_roles("admin")
def creditors_add_installment(creditor_id: int):
    data = request.get_json(silent=True, force=True) or {}
    add_installment(creditor_id, data.get("amount", 0), data.get("date"), data.get("notes"))
    return jsonify({"status": "success"})