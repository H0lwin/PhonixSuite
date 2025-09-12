# -*- coding: utf-8 -*-
"""Global English->Persian status and enum mapping for frontend display.
Use these helpers to ensure UI always shows Persian labels.
"""

STATUS_MAP_FA = {
    # Loan
    "available": "موجود",
    "purchased": "خرید شده",
    "failed": "فروش رفته",
    # Employee
    "active": "فعال",
    "inactive": "غیرفعال",
    # Branch (if used)
    "open": "باز",
    "closed": "بسته",
    # Buyer processing
    "request_registered": "درخواست ثبت شد",
    "under_review": "در حال بررسی",
    "rights_transfer": "انتقال حقوق",
    "bank_validation": "اعتبارسنجی بانکی",
    "loan_paid": "وام پرداخت شد",
    "guarantor_issue": "ضامن ناقص",
    "borrower_issue": "اطلاعات وام‌گیرنده ناقص",
}

def t_status(en_value: str) -> str:
    return STATUS_MAP_FA.get((en_value or "").lower(), en_value)