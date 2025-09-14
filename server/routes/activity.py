# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.auth import require_roles
from models.activity import list_logs

bp_activity = Blueprint("activity", __name__, url_prefix="/api/activity")

@bp_activity.get("")
@require_roles("admin")
def activity_list():
    user_id = request.args.get("user_id", type=int)
    df = request.args.get("date_from", type=str)
    dt = request.args.get("date_to", type=str)
    limit = request.args.get("limit", default=1000, type=int)
    date_from = date_to = None
    try:
        if df:
            date_from = datetime.strptime(df, "%Y-%m-%d").date()
        if dt:
            date_to = datetime.strptime(dt, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"status": "error", "message": "Invalid date format"}), 400
    items = list_logs(user_id=user_id, date_from=date_from, date_to=date_to, limit=limit)
    return jsonify({"status": "success", "items": items})