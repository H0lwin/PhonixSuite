# -*- coding: utf-8 -*-
"""Activity Report (ادمین)
- فیلتر کاربر + تاریخ شمسی
- جدول: زمان، کاربر، اقدام، جزئیات، وضعیت
- پاک کردن فیلترها
"""
from __future__ import annotations
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QGroupBox
)
from PySide6.QtCore import Qt

from client.services import api_client
from client.components.jalali_date import JalaliDateEdit, to_jalali_dt_str

API_EMP_LIST = "http://127.0.0.1:5000/api/employees"
API_ACTIVITY = "http://127.0.0.1:5000/api/activity"


class ActivityView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._employees: List[Dict[str, Any]] = []
        self._build_ui()
        self._load_employees()
        self._refresh()

    def _build_ui(self):
        self.setLayoutDirection(Qt.RightToLeft)
        root = QVBoxLayout(self); root.setSpacing(10); root.setContentsMargins(12,12,12,12)
        title = QLabel("گزارش فعالیت"); title.setStyleSheet("font-size:20px;font-weight:800;")
        root.addWidget(title)

        # Filters
        box = QGroupBox("فیلترها")
        fl = QHBoxLayout(box); fl.setSpacing(8)
        self.cb_employee = QComboBox(); self.cb_employee.addItem("همه کاربران", -1)
        self.date_from = JalaliDateEdit(); self.date_to = JalaliDateEdit()
        btn_clear = QPushButton("پاک کردن فیلترها"); btn_clear.clicked.connect(self._clear)
        btn_refresh = QPushButton("نوسازی"); btn_refresh.clicked.connect(self._refresh)
        for b in (btn_clear, btn_refresh):
            b.setStyleSheet("QPushButton{background:#0d6efd;color:#fff;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#0b5ed7}")
        fl.addWidget(QLabel("کاربر")); fl.addWidget(self.cb_employee)
        fl.addWidget(QLabel("از تاریخ")); fl.addWidget(self.date_from)
        fl.addWidget(QLabel("تا تاریخ")); fl.addWidget(self.date_to)
        fl.addStretch(1); fl.addWidget(btn_clear); fl.addWidget(btn_refresh)
        root.addWidget(box)

        # Table
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["زمان", "کاربر", "اقدام", "جزئیات", "وضعیت"]) 
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.verticalHeader().setDefaultSectionSize(42)
        root.addWidget(self.tbl)

    def _load_employees(self):
        try:
            data = api_client.parse_json(api_client.get(API_EMP_LIST))
        except Exception:
            data = {"status": "error"}
        if data.get("status") == "success":
            self._employees = data.get("items", [])
            for e in self._employees:
                self.cb_employee.addItem(e.get("full_name"), e.get("id"))

    def _clear(self):
        self.cb_employee.setCurrentIndex(0)
        self.date_from.le.setText("")
        self.date_to.le.setText("")
        self._refresh()

    def _refresh(self):
        params = []
        emp_id = self.cb_employee.currentData()
        if emp_id and emp_id != -1:
            params.append(f"user_id={emp_id}")
        df = self.date_from.get_gregorian_iso()
        dt = self.date_to.get_gregorian_iso()
        if df:
            params.append(f"date_from={df}")
        if dt:
            params.append(f"date_to={dt}")
        url = API_ACTIVITY + ("?" + "&".join(params) if params else "")
        try:
            data = api_client.parse_json(api_client.get(url))
        except Exception:
            data = {"status": "error"}
        items = data.get("items", []) if data.get("status") == "success" else []
        self._render(items)

    def _render(self, items: List[Dict[str, Any]]):
        self.tbl.setRowCount(0)
        for it in items:
            row = self.tbl.rowCount(); self.tbl.insertRow(row)
            vals = [
                to_jalali_dt_str(it.get("created_at")),
                str(it.get("user_name") or ""),
                str(it.get("action") or ""),
                str(it.get("details") or ""),
                ("موفق" if it.get("status") == "success" else "خطا" if it.get("status") == "error" else "ناموفق"),
            ]
            for c,v in enumerate(vals):
                self.tbl.setItem(row, c, QTableWidgetItem(v))