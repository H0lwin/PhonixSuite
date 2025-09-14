# -*- coding: utf-8 -*-
"""Employee Dashboard Overview - Limited access version
- Active loans count
- Registered buyers count  
- Recent activities (read-only)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout, QTableWidgetItem, QHeaderView
from client.components.styled_table import StyledTableWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from client.services import api_client
from client.state import session as client_session
from client.components.jalali_date import to_jalali_dt_str

API_LOANS = "http://127.0.0.1:5000/api/loans"
API_BUYERS = "http://127.0.0.1:5000/api/loan-buyers"
API_CREDITORS = "http://127.0.0.1:5000/api/creditors"
API_RECENT = "http://127.0.0.1:5000/api/activity"


class EmployeeOverview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_cards()
        self._load_recent()

    def _build_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(16,16,16,16)
        
        # Get user info
        display_name = client_session.get_display_name() or "کاربر"
        title = QLabel(f"خوش آمدید، {display_name}")
        title.setAlignment(Qt.AlignmentFlag.AlignRight)
        title.setStyleSheet("font-size:22px; font-weight:800; margin-bottom:6px;")
        v.addWidget(title)

        # Cards container (responsive row) - REMOVED active creditors card
        cards = QHBoxLayout(); cards.setSpacing(12)
        self.card_active_loans = self._make_card("💰 وام‌های فعال", "0", "تعداد وام‌های موجود که می‌توانید مشاهده کنید.")
        self.card_my_buyers = self._make_card("👥 خریداران ثبت‌شده", "0", "تعداد خریداران ثبت‌شده توسط شما.")
        self.card_recent = self._make_card("📊 فعالیت‌های اخیر", "0", "تعداد فعالیت‌های اخیر شما.")
        
        for c in (self.card_active_loans, self.card_my_buyers, self.card_recent):
            cards.addWidget(c)
        v.addLayout(cards)

        # Recent activities (limited view)
        box_recent = QGroupBox("فعالیت‌های اخیر")
        box_recent.setStyleSheet("QGroupBox{font-weight:bold; font-size:14px; padding-top:10px;}")
        vr = QVBoxLayout(box_recent); vr.setSpacing(6)
        self.tbl_recent = StyledTableWidget(0, 3)
        self.tbl_recent.setHorizontalHeaderLabels(["اقدام", "وضعیت", "زمان"]) 
        vr.addWidget(self.tbl_recent)
        v.addWidget(box_recent)

    def _make_card(self, title: str, value: str, desc: str):
        box = QGroupBox(title)
        box.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #e9ecef; border-radius:10px; padding-top:16px;} QWidget{background:white}")
        v = QVBoxLayout(box); v.setSpacing(4)
        lbl_val = QLabel(value); lbl_val.setStyleSheet("font-size:22px; font-weight:900; margin:4px 0;")
        lbl_desc = QLabel(desc); lbl_desc.setStyleSheet("color:#6c757d;")
        v.addWidget(lbl_val)
        v.addWidget(lbl_desc)
        box.setProperty("value_label", lbl_val)
        return box

    def _load_cards(self):
        # Active loans count (for employee - only available/non-purchased loans)
        try:
            data = api_client.parse_json(api_client.get(API_LOANS))
            if data.get("status") == "success":
                # Employee sees only available loans
                active_loans = [item for item in data.get("items", []) 
                               if str(item.get("loan_status", "")).lower() != "purchased"]
                self.card_active_loans.property("value_label").setText(str(len(active_loans)))
            else:
                self.card_active_loans.property("value_label").setText("خطا")
        except Exception:
            self.card_active_loans.property("value_label").setText("خطا")

        # My buyers count
        try:
            data = api_client.parse_json(api_client.get(API_BUYERS))
            if data.get("status") == "success":
                # All buyers returned should be employee's own buyers due to backend filtering
                buyer_count = len(data.get("items", []))
                self.card_my_buyers.property("value_label").setText(str(buyer_count))
            else:
                self.card_my_buyers.property("value_label").setText("خطا")
        except Exception:
            self.card_my_buyers.property("value_label").setText("خطا")

        # Active creditors count - REMOVED as per user request
        # This section previously loaded creditor data but caused 403 errors
        # and was requested to be removed from the dashboard overview

    def _load_recent(self):
        try:
            # Get recent activities for current user
            data = api_client.parse_json(api_client.get(API_RECENT + "?limit=5"))
        except Exception:
            data = {"status": "error"}
        
        # Safely handle the response
        if data.get("status") == "success":
            items = data.get("items", [])
        else:
            items = []
        
        self.tbl_recent.setRowCount(0)
        
        # Update recent activities card
        self.card_recent.property("value_label").setText(str(len(items)))
        
        # Show recent activities in table (limited to employee's own activities)
        for item_data in items[:5]:  # Limit to 5 recent activities
            if isinstance(item_data, dict):  # Safety check
                r = self.tbl_recent.rowCount(); self.tbl_recent.insertRow(r)
                
                # Make action more human-readable
                action = self._humanize_action(item_data.get("action", ""))
                
                vals = [
                    action,
                    ("✅ موفق" if item_data.get("status") == "success" else "❌ خطا" if item_data.get("status") == "error" else "⚠️ ناموفق"),
                    to_jalali_dt_str(item_data.get("created_at")),
                ]
                for c, v in enumerate(vals):
                    self.tbl_recent.setItem(r, c, QTableWidgetItem(v))
    
    def _humanize_action(self, action: str) -> str:
        """Convert technical action names to human-readable Persian"""
        action_map = {
            "login": "🔐 ورود به سیستم",
            "logout": "🚪 خروج از سیستم", 
            "attendance_check_in": "⏰ ثبت ورود",
            "attendance_check_out": "⏰ ثبت خروج",
            "loan_create": "💰 ایجاد وام جدید",
            "loan_update": "📝 ویرایش وام",
            "loan_delete": "🗑️ حذف وام",
            "employee_create": "👤 ایجاد کارمند جدید",
            "employee_update": "✏️ ویرایش اطلاعات کارمند",
            "employee_delete": "❌ حذف کارمند",
            "branch_create": "🏢 ایجاد شعبه جدید",
            "branch_update": "🏢 ویرایش شعبه",
            "branch_delete": "🏢 حذف شعبه",
            "finance_transaction": "💳 تراکنش مالی",
            "creditor_create": "💰 ایجاد بستانکار",
            "creditor_update": "💰 ویرایش بستانکار",
            "creditor_settle": "✅ تسویه بستانکار",
            "buyer_create": "👥 ثبت خریدار جدید",
            "buyer_update": "👥 ویرایش خریدار",
        }
        return action_map.get(action, f"📋 {action}")