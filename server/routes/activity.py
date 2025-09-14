# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from utils.auth import require_roles, require_auth
from models.activity import list_logs

bp_activity = Blueprint("activity", __name__, url_prefix="/api/activity")

@bp_activity.get("")
@require_auth
def activity_list():
    """Get activity logs based on user role:
    - Admin: sees all logs with full filtering
    - Employee: sees only their own recent activities (limited)
    """
    user = g.user
    role = user.get("role")
    user_id_param = request.args.get("user_id", type=int)
    df = request.args.get("date_from", type=str)
    dt = request.args.get("date_to", type=str)
    limit = request.args.get("limit", default=1000, type=int)
    
    # Role-based access control
    if role == "admin":
        # Admin can see all logs and use all filters
        user_id = user_id_param
    else:
        # Employee can only see their own activities, limited to recent ones
        user_id = user.get("user_id")
        limit = min(limit, 50)  # Limit employees to max 50 recent activities
        # Ignore date filters for employees to keep it simple
        df = dt = None
    
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