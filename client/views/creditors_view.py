# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGroupBox, QTabWidget, QMenu
)
from PySide6.QtCore import Qt

from client.services import api_client
from client.components.creditor_dialogs import (
    CreditorAddDialog, CreditorEditDialog, CreditorViewDialog, PayDialog
)

API_CREDITORS = "/api/creditors"


class CreditorsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(); layout.setSpacing(12)

        # Tabs: Active / Settled
        self.tabs = QTabWidget()
        # Style tabs similar to Buyers tabs (active highlight)
        self.tabs.setStyleSheet(
            "QTabBar::tab{background:#f1f3f5;color:#212529;padding:6px 12px;border:1px solid #dee2e6;border-top-left-radius:6px;border-top-right-radius:6px;}"
            " QTabBar::tab:selected{background:#0d6efd;color:white;border-color:#0d6efd;}"
            " QTabWidget::pane{border:1px solid #dee2e6; top:-1px;}"
        )
        self.tab_active = QWidget(); active_layout = QVBoxLayout(); active_layout.setSpacing(12); self.tab_active.setLayout(active_layout)
        self.tab_settled = QWidget(); settled_layout = QVBoxLayout(); settled_layout.setSpacing(12); self.tab_settled.setLayout(settled_layout)
        self.tabs.addTab(self.tab_active, "بستانکاران فعال")
        self.tabs.addTab(self.tab_settled, "بستانکاران تسویه شده")
        layout.addWidget(self.tabs)
        # Reload when switching tabs
        self.tabs.currentChanged.connect(lambda _: self._load_all())

        # Active: Search + Add + Refresh
        bar = QHBoxLayout(); bar.setSpacing(8)
        self.in_search = QLineEdit(); self.in_search.setPlaceholderText("جستجو نام بستانکار")
        btn_add = QPushButton("افزودن بستانکار")
        btn_add.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#0b5ed7}")
        btn_add.clicked.connect(self._open_add)
        btn_refresh = QPushButton("نوسازی")
        btn_refresh.setStyleSheet("QPushButton{background:#6c757d;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#5c636a}")
        btn_refresh.clicked.connect(self._load_all)
        bar.addWidget(self.in_search); bar.addStretch(1); bar.addWidget(btn_refresh); bar.addWidget(btn_add)
        active_layout.addLayout(bar)

        # Active Table
        self.tbl_active = QTableWidget(0, 7)
        self.tbl_active.setHorizontalHeaderLabels([
            "نام", "مبلغ کل", "مبلغ پرداخت", "باقیمانده", "وضعیت", "پرداخت", "عملیات"
        ])
        self.tbl_active.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_active.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_active.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_active.setAlternatingRowColors(True)
        self.tbl_active.verticalHeader().setDefaultSectionSize(50)
        active_layout.addWidget(self.tbl_active)

        # Settled: Refresh bar
        settled_bar = QHBoxLayout(); settled_bar.setSpacing(8)
        btn_refresh_settled = QPushButton("نوسازی")
        btn_refresh_settled.setStyleSheet("QPushButton{background:#6c757d;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#5c636a}")
        btn_refresh_settled.clicked.connect(self._load_all)
        settled_bar.addStretch(1); settled_bar.addWidget(btn_refresh_settled)
        settled_layout.addLayout(settled_bar)

        # Settled Table
        self.tbl_settled = QTableWidget(0, 6)
        self.tbl_settled.setHorizontalHeaderLabels([
            "نام", "مبلغ کل", "مبلغ پرداخت", "باقیمانده", "وضعیت", "عملیات"
        ])
        self.tbl_settled.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_settled.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_settled.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_settled.setAlternatingRowColors(True)
        self.tbl_settled.verticalHeader().setDefaultSectionSize(50)
        settled_layout.addWidget(self.tbl_settled)

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignCenter)
        active_layout.addWidget(self.lbl_status)

        self.in_search.textChanged.connect(self._apply_filters)
        self.tabs.currentChanged.connect(lambda _: self._load_all())

        self._all_active: List[Dict[str, Any]] = []
        self._all_settled: List[Dict[str, Any]] = []
        self.setLayout(layout)
        self.setStyleSheet("QWidget{background:white;color:black;}")
        self._load_all()

        # Expose a refresh hook so navigation can re-fetch on page load
        self._load_data = self._load_all

    def _open_add(self):
        dlg = CreditorAddDialog(self)
        if dlg.exec():
            self._load_all()

    def _load_all(self):
        try:
            a = api_client.get(f"{API_CREDITORS}?status=unsettled").json()
            s = api_client.get(f"{API_CREDITORS}?status=settled").json()
        except Exception:
            self.lbl_status.setText("بارگذاری لیست بستانکاران ناموفق بود.")
            return
        if a.get("status") == "success":
            self._all_active = a.get("items", [])
        else:
            self._all_active = []
        if s.get("status") == "success":
            self._all_settled = s.get("items", [])
        else:
            self._all_settled = []
        self._apply_filters()

    def _apply_filters(self):
        txt = (self.in_search.text() or "").strip().lower()
        def match(it: Dict[str, Any]):
            if not txt:
                return True
            return txt in (it.get("full_name") or "").lower()
        active = [it for it in self._all_active if match(it)]
        settled = [it for it in self._all_settled if match(it)]
        self._render_active(active)
        self._render_settled(settled)
        self.lbl_status.setText("" if (active or settled) else "رکوردی وجود ندارد.")

    def _render_active(self, items: List[Dict[str, Any]]):
        self.tbl_active.setRowCount(0)
        for it in items:
            r = self.tbl_active.rowCount(); self.tbl_active.insertRow(r)
            self.tbl_active.setItem(r, 0, QTableWidgetItem(it.get("full_name", "")))
            # amounts
            def fmt(v):
                try:
                    return f"{float(v or 0):,.2f}"
                except Exception:
                    return str(v or "")
            total = fmt(it.get("amount")); paid = fmt(it.get("paid_amount")); remaining = fmt(it.get("remaining_amount"))
            amt_item = QTableWidgetItem(total); amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            paid_item = QTableWidgetItem(paid); paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rem_item = QTableWidgetItem(remaining); rem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tbl_active.setItem(r, 1, amt_item)
            self.tbl_active.setItem(r, 2, paid_item)
            self.tbl_active.setItem(r, 3, rem_item)
            self.tbl_active.setItem(r, 4, QTableWidgetItem(it.get("settlement_status", "")))
            # Pay button
            btn_pay = QPushButton("پرداخت")
            btn_pay.setStyleSheet("QPushButton{background:#198754;color:white;padding:6px 10px;border-radius:4px;} QPushButton:hover{opacity:0.9}")
            btn_pay.clicked.connect(lambda _, _it=it: self._open_pay(_it))
            self.tbl_active.setCellWidget(r, 5, btn_pay)
            # Actions: compact icon buttons (👁️ ✏️ 🗑️)
            actions = QWidget(); hl = QHBoxLayout(actions); hl.setContentsMargins(0,0,0,0); hl.setSpacing(4)
            btn_view = QPushButton("👁️"); btn_edit = QPushButton("✏️"); btn_del = QPushButton("🗑️")
            for b in (btn_view, btn_edit, btn_del):
                b.setFixedSize(28, 28)
                b.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
            btn_view.clicked.connect(lambda _, _it=it: self._open_view(_it))
            btn_edit.clicked.connect(lambda _, _it=it: self._open_edit(_it))
            btn_del.clicked.connect(lambda _, _it=it: self._delete(_it))
            hl.addWidget(btn_view); hl.addWidget(btn_edit); hl.addWidget(btn_del); hl.addStretch(1)
            self.tbl_active.setCellWidget(r, 6, actions)

    def _render_settled(self, items: List[Dict[str, Any]]):
        self.tbl_settled.setRowCount(0)
        for it in items:
            r = self.tbl_settled.rowCount(); self.tbl_settled.insertRow(r)
            self.tbl_settled.setItem(r, 0, QTableWidgetItem(it.get("full_name", "")))
            def fmt(v):
                try:
                    return f"{float(v or 0):,.2f}"
                except Exception:
                    return str(v or "")
            total = fmt(it.get("amount")); paid = fmt(it.get("paid_amount")); remaining = fmt(it.get("remaining_amount"))
            amt_item = QTableWidgetItem(total); amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            paid_item = QTableWidgetItem(paid); paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rem_item = QTableWidgetItem(remaining); rem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tbl_settled.setItem(r, 1, amt_item)
            self.tbl_settled.setItem(r, 2, paid_item)
            self.tbl_settled.setItem(r, 3, rem_item)
            self.tbl_settled.setItem(r, 4, QTableWidgetItem(it.get("settlement_status", "")))
            # Actions: compact icon buttons (👁️ ✏️ 🗑️)
            actions = QWidget(); hl = QHBoxLayout(actions); hl.setContentsMargins(0,0,0,0); hl.setSpacing(4)
            btn_view = QPushButton("👁️"); btn_edit = QPushButton("✏️"); btn_del = QPushButton("🗑️")
            for b in (btn_view, btn_edit, btn_del):
                b.setFixedSize(28, 28)
                b.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
            btn_view.clicked.connect(lambda _, _it=it: self._open_view(_it))
            btn_edit.clicked.connect(lambda _, _it=it: self._open_edit(_it))
            btn_del.clicked.connect(lambda _, _it=it: self._delete(_it))
            hl.addWidget(btn_view); hl.addWidget(btn_edit); hl.addWidget(btn_del); hl.addStretch(1)
            self.tbl_settled.setCellWidget(r, 5, actions)

    def _open_view(self, it: Dict[str, Any]):
        dlg = CreditorViewDialog(it.get("id"), self)
        dlg.exec()

    def _open_edit(self, it: Dict[str, Any]):
        dlg = CreditorEditDialog(it.get("id"), self)
        if dlg.exec():
            self._load_all()

    def _open_pay(self, it: Dict[str, Any]):
        dlg = PayDialog(it.get("id"), it.get("full_name",""), float(it.get("amount") or 0), self)
        if dlg.exec():
            self._load_all()

    def _delete(self, it: Dict[str, Any]):
        from PySide6.QtWidgets import QMessageBox
        m = QMessageBox.question(self, "حذف بستانکار", "آیا از حذف این بستانکار اطمینان دارید؟")
        if m == QMessageBox.StandardButton.Yes:
            try:
                r = api_client.delete(f"{API_CREDITORS}/{it.get('id')}")
                data = r.json()
                if data.get("status") == "success":
                    self._load_all()
                else:
                    QMessageBox.warning(self, "خطا", data.get("message", "حذف ناموفق بود."))
            except Exception:
                QMessageBox.critical(self, "خطا", "حذف ناموفق بود.")
