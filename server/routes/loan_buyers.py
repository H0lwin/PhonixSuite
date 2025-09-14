# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, g
from models.loan_buyer import ensure_loan_buyer_schema, create_loan_buyer, update_loan_buyer, list_loan_buyers_for_user, get_loan_buyer, get_loan_buyer_history, delete_loan_buyer
from models.activity import add_log
from utils.auth import require_roles, require_auth, require_admin, require_admin_or_owner

bp_loan_buyers = Blueprint("loan_buyers", __name__, url_prefix="/api/loan-buyers")


@bp_loan_buyers.get("")
@require_auth
def lb_list():
    """Get loan buyers list based on user role:
    - Admin: sees all buyers
    - Employee: sees only their own created buyers
    """
    user = g.user
    role = user.get("role")
    username = user.get("national_id")
    
    # Updated logic: admin sees all, employees see only their own
    if role == "admin":
        items = list_loan_buyers_for_user(user_role="admin", username=None)
    else:
        # Employee/broker sees only own created records
        items = list_loan_buyers_for_user(user_role="employee", username=username)
    
    return jsonify({"status": "success", "items": items})


@bp_loan_buyers.post("")
@require_auth  # Any authenticated user can create loan buyers
def lb_create():
    """Create a new loan buyer record.
    Users can only create records for themselves (tracked by creator metadata).
    """
    user = g.user
    data = request.get_json(silent=True, force=True) or {}
    
    # Always add creator metadata for ownership tracking
    data["created_by_name"] = user.get("full_name") or user.get("national_id")
    data["created_by_nid"] = user.get("national_id")
    
    # For backward compatibility with broker field
    if not data.get("broker") and user.get("role") in ["broker", "employee"]:
        data["broker"] = user.get("national_id")
    
    try:
        buyer_id = create_loan_buyer(data)
        # Log successful buyer creation
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "create_buyer", 
            f"buyer_id={buyer_id}, loan_id={data.get('loan_id')}, name={data.get('full_name')}", 
            "success"
        )
        return jsonify({"status": "success", "id": buyer_id})
    except Exception as e:
        # Log failed buyer creation
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "create_buyer", 
            f"error: {str(e)}", 
            "error"
        )
        raise


@bp_loan_buyers.patch("/<int:buyer_id>")
@require_admin_or_owner("loan_buyer", "buyer_id")
def lb_update(buyer_id: int):
    """Update a loan buyer record.
    - Admin: can update any record
    - Employee: can only update their own created records
    """
    user = g.user
    data = request.get_json(silent=True, force=True) or {}
    
    # Additional check for existing record
    from database import get_connection
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("SELECT id FROM loan_buyers WHERE id=%s LIMIT 1", (buyer_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        return jsonify({"status": "error", "message": "Not found"}), 404
    cur.close(); conn.close()
    
    try:
        update_loan_buyer(buyer_id, data)
        # Log successful buyer update
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "update_buyer", 
            f"buyer_id={buyer_id}", 
            "success"
        )
        return jsonify({"status": "success"})
    except Exception as e:
        # Log failed buyer update
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "update_buyer", 
            f"buyer_id={buyer_id}, error: {str(e)}", 
            "error"
        )
        raise


@bp_loan_buyers.get("/<int:buyer_id>")
@require_admin_or_owner("loan_buyer", "buyer_id")
def lb_detail(buyer_id: int):
    """Get loan buyer details.
    - Admin: can view any record
    - Employee: can only view their own created records
    """
    item = get_loan_buyer(buyer_id)
    if not item:
        return jsonify({"status": "error", "message": "Not found"}), 404
    
    return jsonify({"status": "success", "item": item})


@bp_loan_buyers.get("/<int:buyer_id>/history")
@require_admin  # Only admin can view history
def lb_history(buyer_id: int):
    """Get loan buyer status history (Admin only)"""
    hist = get_loan_buyer_history(buyer_id)
    return jsonify({"status": "success", "items": hist})


@bp_loan_buyers.delete("/<int:buyer_id>")
@require_admin_or_owner("loan_buyer", "buyer_id")
def lb_delete(buyer_id: int):
    """Delete a loan buyer record.
    - Admin: can delete any record
    - Employee: can only delete their own created records
    """
    user = g.user
    # Get buyer info before deletion for logging
    item = get_loan_buyer(buyer_id)
    
    try:
        delete_loan_buyer(buyer_id)
        # Log successful buyer deletion
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "delete_buyer", 
            f"buyer_id={buyer_id}, name={item.get('full_name') if item else 'unknown'}", 
            "success"
        )
        return jsonify({"status": "success"})
    except Exception as e:
        # Log failed buyer deletion
        add_log(
            user.get("user_id"), 
            user.get("full_name"), 
            "delete_buyer", 
            f"buyer_id={buyer_id}, error: {str(e)}", 
            "error"
        )
        raise
