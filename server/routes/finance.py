# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from models.finance import ensure_finance_schema, add_revenue, add_expense, monthly_summary
from utils.auth import require_roles

bp_finance = Blueprint("finance", __name__, url_prefix="/api/finance")


@bp_finance.post("/revenue")
@require_roles("admin", "accountant")
def finance_add_revenue():
    data = request.get_json(silent=True, force=True) or {}
    add_revenue(data.get("source"), data.get("amount", 0), data.get("ref_id"), data.get("ref_type"))
    return jsonify({"status": "success"})


@bp_finance.post("/expense")
@require_roles("admin", "accountant")
def finance_add_expense():
    data = request.get_json(silent=True, force=True) or {}
    add_expense(data.get("source"), data.get("amount", 0), data.get("ref_id"), data.get("ref_type"))
    return jsonify({"status": "success"})


@bp_finance.get("/summary/<int:year>/<int:month>")
@require_roles("admin", "accountant")
def finance_summary(year: int, month: int):
    return jsonify({"status": "success", "summary": monthly_summary(year, month)})