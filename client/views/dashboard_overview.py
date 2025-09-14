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
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, QTimer

from client.services import api_client
from client.state import session as client_session
from client.components.jalali_date import to_jalali_dt_str

API_RECENT = "http://127.0.0.1:5000/api/activity"
API_EMP_LIST = "http://127.0.0.1:5000/api/employees"
API_FIN_METRICS = "http://127.0.0.1:5000/api/finance/metrics"
API_LOANS = "http://127.0.0.1:5000/api/loans"
API_ATT_ADMIN = "http://127.0.0.1:5000/api/attendance/admin"


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
        self.card_active_emps = self._make_card("👤 کارکنان فعال", "0", "تعداد کل کارکنان با وضعیت فعال.")
        self.card_pending_leave = self._make_card("🕒 در انتظار تأیید", "0", "تعداد درخواست‌های مرخصی در انتظار تأیید.")
        self.card_month_income = self._make_card("📈 درآمد ماهانه", "۰ تومان", "سود تخمینی این ماه (از محاسبات مالی).")
        for c in (self.card_total_loans, self.card_active_emps, self.card_pending_leave, self.card_month_income):
            cards.addWidget(c)
        v.addLayout(cards)

        # Recent activities
        box_recent = QGroupBox("فعالیت‌های اخیر")
        box_recent.setStyleSheet("QGroupBox{font-weight:bold}")
        vr = QVBoxLayout(box_recent); vr.setSpacing(6)
        self.tbl_recent = QTableWidget(0, 4)
        self.tbl_recent.setHorizontalHeaderLabels(["کاربر", "اقدام", "وضعیت", "زمان"]) 
        self.tbl_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_recent.setStyleSheet("QHeaderView::section{background:#f8f9fa; padding:6px; border:1px solid #e9ecef;} QTableWidget{background:white;}")
        vr.addWidget(self.tbl_recent)
        v.addWidget(box_recent)

        # Attendance summary (today)
        self.box_att = QGroupBox("پیگیری حضور و غیاب (امروز)")
        self.box_att.setStyleSheet("QGroupBox{font-weight:bold}")
        va = QVBoxLayout(self.box_att)
        self.lbl_attendance = QLabel("در حال بارگذاری...")
        va.addWidget(self.lbl_attendance)
        v.addWidget(self.box_att)

        # Current session (countdown)
        box_sess = QGroupBox("جلسه کاری فعلی شما")
        box_sess.setStyleSheet("QGroupBox{font-weight:bold}")
        vs = QVBoxLayout(box_sess)
        disp = client_session.get_display_name() or "کاربر"
        role = client_session.get_role() or "user"
        self.lbl_sess_info = QLabel(f"کاربر: {disp} | نقش: {role}")
        self.lbl_sess_timer = QLabel("زمان باقیمانده: 60:00")
        self.lbl_sess_timer.setStyleSheet("font-size:14px; font-weight:600")
        vs.addWidget(self.lbl_sess_info)
        vs.addWidget(self.lbl_sess_timer)
        v.addWidget(box_sess)

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
        # total loan value (sum of purchase_rate)
        try:
            data = api_client.parse_json(api_client.get(API_LOANS))
        except Exception:
            data = {"status": "error"}
        total = 0
        if data.get("status") == "success":
            for it in data.get("items", []):
                try:
                    total += float(it.get("purchase_rate") or 0)
                except Exception:
                    pass
        self.card_total_loans._value_label.setText(f"{int(total):,} تومان".replace(",", ","))

        # active employees
        try:
            emps = api_client.parse_json(api_client.get(API_EMP_LIST))
        except Exception:
            emps = {"status": "error"}
        active_cnt = 0
        if emps.get("status") == "success":
            active_cnt = sum(1 for e in emps.get("items", []) if (e.get("status") == "active"))
        self._active_count = active_cnt
        self.card_active_emps._value_label.setText(str(active_cnt))

        # monthly income (placeholder -> use finance metrics if available)
        try:
            met = api_client.parse_json(api_client.get(API_FIN_METRICS))
            if met.get("status") == "success":
                m = float(met.get("metrics", {}).get("monthly_income", 0))
                self.card_month_income._value_label.setText(f"{int(m):,} تومان".replace(",", ","))
        except Exception:
            pass

    def _load_recent(self):
        try:
            data = api_client.parse_json(api_client.get(API_RECENT + "?limit=10"))
        except Exception:
            data = {"status": "error"}
        items = data.get("items", []) if data.get("status") == "success" else []
        self.tbl_recent.setRowCount(0)
        for it in items[:10]:
            r = self.tbl_recent.rowCount(); self.tbl_recent.insertRow(r)
            vals = [
                str(it.get("user_name") or ""),
                str(it.get("action") or ""),
                ("موفق" if it.get("status") == "success" else "خطا" if it.get("status") == "error" else "ناموفق"),
                to_jalali_dt_str(it.get("created_at")),
            ]
            for c, v in enumerate(vals):
                self.tbl_recent.setItem(r, c, QTableWidgetItem(v))

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
        if self._active_count:
            self.lbl_attendance.setText(f"امروز: حاضر {present} نفر / کل فعال {self._active_count} نفر")
        else:
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