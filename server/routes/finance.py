# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, g
from models.finance import (
    ensure_finance_schema, add_revenue, add_expense, monthly_summary,
    get_financial_metrics, get_six_month_trend, list_transactions, delete_transaction
)
from utils.auth import require_roles
from models.activity import add_log

bp_finance = Blueprint("finance", __name__, url_prefix="/api/finance")


@bp_finance.post("/revenue")
@require_roles("admin", "accountant")
def finance_add_revenue():
    data = request.get_json(silent=True, force=True) or {}
    add_revenue(data.get("source"), data.get("amount", 0), data.get("ref_id"), data.get("ref_type"))
    # Log
    user_id = getattr(g, "user", {}).get("user_id") if hasattr(g, "user") else None
    user_name = getattr(g, "user", {}).get("full_name") if hasattr(g, "user") else None
    add_log(user_id, user_name, "add_revenue", f"source={data.get('source')}, amount={data.get('amount')}", "success")
    return jsonify({"status": "success"})


@bp_finance.post("/expense")
@require_roles("admin", "accountant")
def finance_add_expense():
    data = request.get_json(silent=True, force=True) or {}
    add_expense(data.get("source"), data.get("amount", 0), data.get("ref_id"), data.get("ref_type"))
    user_id = getattr(g, "user", {}).get("user_id") if hasattr(g, "user") else None
    user_name = getattr(g, "user", {}).get("full_name") if hasattr(g, "user") else None
    add_log(user_id, user_name, "add_expense", f"source={data.get('source')}, amount={data.get('amount')}", "success")
    return jsonify({"status": "success"})


@bp_finance.get("/summary/<int:year>/<int:month>")
@require_roles("admin", "accountant")
def finance_summary(year: int, month: int):
    return jsonify({"status": "success", "summary": monthly_summary(year, month)})


@bp_finance.get("/metrics")
@require_roles("admin", "accountant")
def finance_metrics():
    """Get key financial metrics for dashboard"""
    try:
        metrics = get_financial_metrics()
        return jsonify({"status": "success", "metrics": metrics})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp_finance.get("/trend")
@require_roles("admin", "accountant")
def finance_trend():
    """Get 6-month revenue vs expenses trend"""
    try:
        trend_data = get_six_month_trend()
        return jsonify({"status": "success", "trend": trend_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp_finance.get("/transactions")
@require_roles("admin", "accountant")
def finance_transactions():
    """Get all financial transactions (revenues and expenses)"""
    try:
        transactions = list_transactions()
        return jsonify({"status": "success", "transactions": transactions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp_finance.delete("/transactions/<int:transaction_id>")
@require_roles("admin", "accountant")
def delete_finance_transaction(transaction_id: int):
    """Delete a financial transaction"""
    try:
        transaction_type = request.args.get("type", "revenue")  # revenue or expense
        success = delete_transaction(transaction_id, transaction_type)
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
