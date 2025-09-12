# -*- coding: utf-8 -*-
"""
Loan-related domain services.
This module centralizes business side effects (like auto-creating creditors)
so they work regardless of whether updates come from routes or internal code.
"""
from __future__ import annotations
from typing import Dict, Any
import logging

from models.loan import get_loan, update_loan
from models.creditor import create_creditor
from database import get_connection

log = logging.getLogger(__name__)


def _ensure_creditor_for_purchased_loan(loan_id: int):
    """Create a creditor for the given loan if one does not already exist.

    Uses loan fields: owner_full_name, purchase_rate, bank_name.
    """
    # Check if a creditor already exists for this loan
    conn = get_connection(True)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM creditors WHERE loan_id=%s", (loan_id,))
        exists = int(cur.fetchone()[0] or 0)
    except Exception as e:
        log.exception("Creditor existence check failed for loan %s: %s", loan_id, e)
        exists = 0
    finally:
        cur.close()
        conn.close()

    if exists:
        log.info("Creditor already exists for loan %s; skipping creation", loan_id)
        return

    loan = get_loan(loan_id)
    if not loan:
        log.warning("Loan %s not found while ensuring creditor", loan_id)
        return

    full_name = (loan.get("owner_full_name") or "").strip()
    try:
        amount = float(loan.get("purchase_rate") or 0)
    except Exception as e:
        log.exception("Loan %s invalid purchase_rate while ensuring creditor: %s", loan_id, e)
        amount = 0.0
    description = f"loan_id={loan_id}, rate={loan.get('purchase_rate')}, bank={loan.get('bank_name')}"

    if not full_name:
        log.warning("Loan %s owner_full_name is empty; creating creditor with empty name.", loan_id)
    if amount <= 0:
        log.warning("Loan %s purchase_rate is %s; creditor will be created with non-positive amount.", loan_id, amount)

    try:
        cid = create_creditor(
            full_name, amount, description, loan_id=loan_id,
            loan_rate=loan.get('purchase_rate'), bank_name=loan.get('bank_name'), owner_phone=loan.get('owner_phone')
        )
        log.info("Created creditor id=%s for loan %s (name=%s, amount=%s)", cid, loan_id, full_name, amount)
    except Exception as e:
        log.exception("Creating creditor failed for loan %s: %s", loan_id, e)


def update_loan_with_side_effects(loan_id: int, data: Dict[str, Any]):
    """Update loan fields and handle business side effects.

    Specifically: if loan_status changes from not 'purchased' to 'purchased',
    ensure a creditor record exists for this loan.
    """
    pre = get_loan(loan_id)
    if not pre:
        log.warning("Loan %s not found for update", loan_id)
        return

    pre_status = pre.get("loan_status")
    update_loan(loan_id, data)
    post = get_loan(loan_id)
    post_status = (post or {}).get("loan_status")

    # Trigger side-effect on transition to purchased
    if pre_status != "purchased" and post_status == "purchased":
        _ensure_creditor_for_purchased_loan(loan_id)
