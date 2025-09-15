# -*- coding: utf-8 -*-
"""Admin Dashboard Overview (زیباتر و کامل)
- Header greeting
- Cards: total loan value, active employees, pending leave (placeholder), monthly income (placeholder)
- Recent activities (table)
- Attendance summary (today)
- Current session (live countdown)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout, QTableWidgetItem, QHeaderView
from client.components.styled_table import StyledTableWidget
from PySide6.QtCore import Qt, QTimer

from client.services import api_client
from client.state import session as client_session
from client.components.jalali_date import to_jalali_dt_str

API_RECENT = "/api/activity"
API_EMP_LIST = "/api/employees"
API_FIN_METRICS = "/api/finance/metrics"
API_LOANS = "/api/loans"
API_ATT_ADMIN = "/api/attendance/admin"


class DashboardOverview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._session_timer: Optional[QTimer] = None
        self._active_count: int = 0
        self._build_ui()
        self._load_cards()
        self._load_recent()
        self._load_attendance_summary()

    # Allow parent to pass session timer for countdown display
    def set_session_timer(self, timer: QTimer):
        self._session_timer = timer
        self._session_countdown.start()

    def _build_ui(self):
        self.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(16,16,16,16)
        title = QLabel("خوش آمدید، مدیر سیستم!")
        title.setAlignment(Qt.AlignRight)
        title.setStyleSheet("font-size:22px; font-weight:800; margin-bottom:6px;")
        v.addWidget(title)

        # Cards container (responsive row)
        cards = QHBoxLayout(); cards.setSpacing(12)
        self.card_total_loans = self._make_card("💰 ارزش کل وام‌ها", "۰ تومان", "مجموع ارزش تمام وام‌های ثبت شده در سیستم.")
        self.card_month_income = self._make_card("📈 درآمد ماهانه", "۰ تومان", "سود تخمینی این ماه (از محاسبات مالی).")
        for c in (self.card_total_loans, self.card_month_income):
            cards.addWidget(c)
        v.addLayout(cards)

        # Recent activities
        box_recent = QGroupBox("فعالیت‌های اخیر")
        box_recent.setStyleSheet("QGroupBox{font-weight:bold; font-size:14px; padding-top:10px;}")
        vr = QVBoxLayout(box_recent); vr.setSpacing(6)
        self.tbl_recent = StyledTableWidget(0, 4)
        self.tbl_recent.setHorizontalHeaderLabels(["کاربر", "اقدام", "وضعیت", "زمان"]) 
        vr.addWidget(self.tbl_recent)
        v.addWidget(box_recent)

        # Bottom row with two sections side by side
        bottom_row = QHBoxLayout(); bottom_row.setSpacing(12)
        
        # Attendance summary (today) - Left side
        self.box_att = QGroupBox("📊 پیگیری حضور و غیاب امروز")
        self.box_att.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 14px; 
                border: 1px solid #e9ecef; 
                border-radius: 8px; 
                padding-top: 15px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 8px;
                color: #495057;
            }
        """)
        va = QVBoxLayout(self.box_att); va.setSpacing(8); va.setContentsMargins(12,12,12,12)
        self.lbl_attendance = QLabel("در حال بارگذاری...")
        self.lbl_attendance.setStyleSheet("font-size:13px; color:#6c757d; padding:8px;")
        va.addWidget(self.lbl_attendance)
        bottom_row.addWidget(self.box_att)

        # Current session (countdown) - Right side
        box_sess = QGroupBox("⏱️ جلسه کاری فعلی")
        box_sess.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 14px; 
                border: 1px solid #e9ecef; 
                border-radius: 8px; 
                padding-top: 15px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 8px;
                color: #495057;
            }
        """)
        vs = QVBoxLayout(box_sess); vs.setSpacing(8); vs.setContentsMargins(12,12,12,12)
        disp = client_session.get_display_name() or "کاربر"
        role = "مدیر سیستم" if client_session.get_role() == "admin" else "کارمند"
        self.lbl_sess_info = QLabel(f"👤 {disp} | 🔑 {role}")
        self.lbl_sess_info.setStyleSheet("font-size:13px; color:#495057; padding:4px;")
        self.lbl_sess_timer = QLabel("⏰ زمان باقیمانده: 60:00")
        self.lbl_sess_timer.setStyleSheet("font-size:14px; font-weight:600; color:#0d6efd; padding:4px;")
        vs.addWidget(self.lbl_sess_info)
        vs.addWidget(self.lbl_sess_timer)
        bottom_row.addWidget(box_sess)
        
        v.addLayout(bottom_row)

        # Periodic refresh: cards
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30000)  # 30s
        self._refresh_timer.timeout.connect(self._load_cards)
        self._refresh_timer.start()

        # 1-second timer to update countdown when provided
        self._session_countdown = QTimer(self)
        self._session_countdown.setInterval(1000)
        self._session_countdown.timeout.connect(self._tick_session)

    def _make_card(self, title: str, value: str, desc: str):
        box = QGroupBox(title)
        box.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #e9ecef; border-radius:10px; padding-top:16px;} QWidget{background:white}")
        v = QVBoxLayout(box); v.setSpacing(4)
        lbl_val = QLabel(value); lbl_val.setStyleSheet("font-size:22px; font-weight:900; margin:4px 0;")
        lbl_desc = QLabel(desc); lbl_desc.setStyleSheet("color:#6c757d;")
        v.addWidget(lbl_val)
        v.addWidget(lbl_desc)
        box._value_label = lbl_val
        return box

    def _load_cards(self):
        # total loan value (available/active only) -> sum of 'amount' excluding purchased/failed/cancelled
        try:
            data = api_client.parse_json(api_client.get(API_LOANS))
        except Exception:
            data = {"status": "error"}
        total = 0.0
        if data.get("status") == "success":
            for it in data.get("items", []):
                try:
                    status = str(it.get("loan_status", "")).lower()
                    if status in ("purchased", "failed", "cancelled"):
                        continue
                    total += float(it.get("amount") or 0)
                except Exception:
                    continue
        self.card_total_loans._value_label.setText(f"{int(total):,} تومان".replace(",", ","))



        # monthly income (placeholder -> use finance metrics if available)
        try:
            from client.state import session as client_session
            role = (client_session.get_role() or "").lower()
            if role not in ("admin", "accountant", "secretary"):
                self.card_month_income._value_label.setText("محدود")
            else:
                resp = api_client.get(API_FIN_METRICS)
                if resp.status_code == 403:
                    self.card_month_income._value_label.setText("محدود")
                else:
                    met = api_client.parse_json(resp)
                    if met.get("status") == "success":
                        m = float(met.get("metrics", {}).get("monthly_income", 0))
                        self.card_month_income._value_label.setText(f"{int(m):,} تومان".replace(",", ","))
        except Exception:
            self.card_month_income._value_label.setText("خطا")

    def _load_recent(self):
        try:
            data = api_client.parse_json(api_client.get(API_RECENT + "?limit=10"))
        except Exception:
            data = {"status": "error"}
        items = data.get("items", []) if data.get("status") == "success" else []
        self.tbl_recent.setRowCount(0)
        for it in items[:10]:
            r = self.tbl_recent.rowCount(); self.tbl_recent.insertRow(r)
            
            # Make action more human-readable
            action = self._humanize_action(it.get("action", ""))
            
            vals = [
                str(it.get("user_name") or ""),
                action,
                ("✅ موفق" if it.get("status") == "success" else "❌ خطا" if it.get("status") == "error" else "⚠️ ناموفق"),
                to_jalali_dt_str(it.get("created_at")),
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
        }
        return action_map.get(action, f"📋 {action}")

    def _load_attendance_summary(self):
        # Today in ISO
        today_iso = date.today().strftime("%Y-%m-%d")
        try:
            data = api_client.parse_json(api_client.get(f"{API_ATT_ADMIN}?date_from={today_iso}&date_to={today_iso}"))
        except Exception:
            data = {"status": "error"}
        present = 0
        if data.get("status") == "success":
            items = data.get("items", [])
            present = len(items)
        self.lbl_attendance.setText(f"امروز: حاضر {present} نفر")

    def _tick_session(self):
        if not self._session_timer:
            self._session_countdown.stop()
            return
        try:
            ms = max(0, self._session_timer.remainingTime())
        except Exception:
            ms = 0
        total_sec = int(ms / 1000)
        mm = total_sec // 60
        ss = total_sec % 60
        self.lbl_sess_timer.setText(f"زمان باقیمانده: {mm:02d}:{ss:02d}")