# -*- coding: utf-8 -*-
"""Admin Attendance View
- Filters: employee dropdown, Jalali date range, clear filters
- Table columns: کارمند، تاریخ (شمسی)، ساعت ورود، ساعت خروج، مجموع ساعت کاری، وضعیت حضور
- Actions: Refresh, Clear Filters
- Localization: Persian labels
"""
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QGroupBox
)
from client.components.styled_table import StyledTableWidget
from PySide6.QtCore import Qt

# Local imports
import logging
from client.services import api_client
from client.components.jalali_date import JalaliDateEdit, gregorian_to_jalali

API_EMP_LIST = "/api/employees"
API_ATT_ADMIN = "/api/attendance/admin"


def _fmt_hms_total(seconds: int) -> str:
    try:
        s = int(seconds or 0)
    except Exception:
        s = 0
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h:02d}:{m:02d}"


class AttendanceView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._employees: List[Dict[str, Any]] = []
        self._build_ui()
        self._load_employees()
        self._refresh()

    def _build_ui(self):
        self.setLayoutDirection(Qt.RightToLeft)
        root = QVBoxLayout(self); root.setSpacing(10); root.setContentsMargins(12,12,12,12)

        title = QLabel("حضور و غیاب")
        title.setStyleSheet("font-size:20px; font-weight:800;")
        title.setAlignment(Qt.AlignRight)
        root.addWidget(title)

        # Filters
        filters = QGroupBox("فیلترها"); filters.setStyleSheet("QGroupBox{font-weight:bold;}")
        fl = QHBoxLayout(filters); fl.setSpacing(8)
        self.cb_employee = QComboBox(); self.cb_employee.setMinimumWidth(220)
        self.cb_employee.addItem("همه کارمندان", -1)
        self.date_from = JalaliDateEdit(); self.date_to = JalaliDateEdit()
        lbl_from = QLabel("از تاریخ (شمسی)")
        lbl_to = QLabel("تا تاریخ (شمسی)")
        btn_clear = QPushButton("پاک کردن فیلترها"); btn_clear.clicked.connect(self._clear_filters)
        btn_refresh = QPushButton("نوسازی"); btn_refresh.clicked.connect(self._refresh)
        for b in (btn_clear, btn_refresh):
            b.setStyleSheet("QPushButton{background:#0d6efd; color:#fff; padding:6px 10px; border-radius:4px;} QPushButton:hover{background:#0b5ed7}")

        fl.addWidget(QLabel("کارمند")); fl.addWidget(self.cb_employee)
        fl.addWidget(lbl_from); fl.addWidget(self.date_from)
        fl.addWidget(lbl_to); fl.addWidget(self.date_to)
        fl.addStretch(1)
        fl.addWidget(btn_clear); fl.addWidget(btn_refresh)
        root.addWidget(filters)

        # Table
        self.tbl = StyledTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["کارمند", "تاریخ", "ساعت ورود", "ساعت خروج", "مجموع ساعت کاری", "وضعیت حضور"])
        root.addWidget(self.tbl)



    def _clear_filters(self):
        self.cb_employee.setCurrentIndex(0)
        # Reset to empty — JalaliDateEdit defaults to 1400-01-01 text but we interpret None via get_gregorian_iso
        self.date_from.le.setText("")
        self.date_to.le.setText("")
        self._refresh()

    def _load_employees(self):
        try:
            resp = api_client.get(API_EMP_LIST)
            data = api_client.parse_json(resp)
        except Exception:
            data = {"status": "error"}
        self.cb_employee.blockSignals(True)
        if data.get("status") == "success":
            self._employees = data.get("items", [])
            for e in self._employees:
                self.cb_employee.addItem(e.get("full_name", ""), e.get("id"))
        self.cb_employee.blockSignals(False)

    def _refresh(self):
        params = []
        emp_id = self.cb_employee.currentData()
        if emp_id and emp_id != -1:
            params.append(f"employee_id={emp_id}")
        # Only add date filters if the text field is not empty (user has actually selected a date)
        df = self.date_from.get_gregorian_iso() if self.date_from.le.text().strip() else None
        dt = self.date_to.get_gregorian_iso() if self.date_to.le.text().strip() else None
        if df:
            params.append(f"date_from={df}")
        if dt:
            params.append(f"date_to={dt}")
        url = API_ATT_ADMIN + ("?" + "&".join(params) if params else "")
        try:
            resp = api_client.get(url)
            data = api_client.parse_json(resp)
        except Exception as e:
            logging.exception("attendance _refresh failed: %s", e)
            data = {"status": "error"}
        items = data.get("items", []) if data.get("status") == "success" else []
        logging.info("attendance items fetched: url=%s count=%s", url, len(items))
        self._render(items)

    def _render(self, items: List[Dict[str, Any]]):
        self.tbl.setRowCount(0)
        for it in items:
            row = self.tbl.rowCount(); self.tbl.insertRow(row)
            # Persian date
            try:
                d = it.get("date");
                if isinstance(d, str):
                    y, m, dd = map(int, d.split("-")[:3])
                else:
                    y, m, dd = d.year, d.month, d.day
                jy, jm, jd = gregorian_to_jalali(y, m, dd)
                pdate = f"{jy:04d}-{jm:02d}-{jd:02d}"
            except Exception:
                pdate = str(it.get("date"))
            total = _fmt_hms_total(it.get("total_seconds", 0))
            status = "حاضر" if (it.get("status") == "present") else "غائب" if (it.get("status") == "absent") else (it.get("status") or "")
            vals = [
                it.get("full_name", ""),
                pdate,
                (it.get("check_in") or "") ,
                (it.get("check_out") or "") ,
                total,
                status,
            ]
            for c, v in enumerate(vals):
                self.tbl.setItem(row, c, QTableWidgetItem(str(v)))
        logging.info("attendance table rendered: rows=%s", self.tbl.rowCount())

