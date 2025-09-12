# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGroupBox, QTabWidget, QAbstractSpinBox
)
from PySide6.QtCore import Qt, QLocale

from ..services import api_client
from ..components.loan_dialogs import (
    LoanAddDialog, LoanEditDialog, LoanViewDialog, delete_loan_with_confirm
)
from ..utils.i18n import t_status

API_LOANS = "http://127.0.0.1:5000/api/loans"


class LoansView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(); layout.setSpacing(12)

        # Tabs: Active Loans and Loan History
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab{background:#f1f3f5;color:#212529;padding:6px 12px;border:1px solid #dee2e6;border-top-left-radius:6px;border-top-right-radius:6px;}"
            " QTabBar::tab:selected{background:#0d6efd;color:white;border-color:#0d6efd;}"
            " QTabWidget::pane{border:1px solid #dee2e6; top:-1px;}"
        )
        self.tab_active = QWidget(); active_layout = QVBoxLayout(); active_layout.setSpacing(12); self.tab_active.setLayout(active_layout)
        self.tab_history = QWidget(); history_layout = QVBoxLayout(); history_layout.setSpacing(12); self.tab_history.setLayout(history_layout)
        self.tabs.addTab(self.tab_active, "وام‌های فعال")
        self.tabs.addTab(self.tab_history, "سوابق وام")
        layout.addWidget(self.tabs)

        # Search + Filters bar
        filters_bar = QHBoxLayout(); filters_bar.setSpacing(8)
        self.in_search = QLineEdit(); self.in_search.setPlaceholderText("جستجو نام بانک / نام مالک")
        self.cb_bank = QComboBox(); self.cb_bank.setMinimumWidth(160); self.cb_bank.addItem("همه بانک‌ها", "")
        self.cb_type = QComboBox(); self.cb_type.setMinimumWidth(150); self.cb_type.addItem("همه نوع وام‌ها", "")
        self.cb_duration = QComboBox(); self.cb_duration.setMinimumWidth(150); self.cb_duration.addItem("همه مدت‌ها", "")
        # Amount range filter (min .. max)
        self.in_amount_min = QDoubleSpinBox(); self.in_amount_min.setRange(0, 10_000_000_000); self.in_amount_min.setDecimals(2); self.in_amount_min.setPrefix(">= ")
        self.in_amount_min.setToolTip("حداقل مبلغ")
        self.in_amount_min.setLocale(QLocale(QLocale.English)); self.in_amount_min.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount_min.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.in_amount_min.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        self.in_amount_min.setValue(0)
        self.in_amount_max = QDoubleSpinBox(); self.in_amount_max.setRange(0, 10_000_000_000); self.in_amount_max.setDecimals(2); self.in_amount_max.setPrefix("<= ")
        self.in_amount_max.setToolTip("حداکثر مبلغ")
        self.in_amount_max.setLocale(QLocale(QLocale.English)); self.in_amount_max.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount_max.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.in_amount_max.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        self.in_amount_max.setValue(0)

        self.in_search.textChanged.connect(self._apply_filters)
        self.cb_bank.currentIndexChanged.connect(self._apply_filters)
        self.cb_type.currentIndexChanged.connect(self._apply_filters)
        self.cb_duration.currentIndexChanged.connect(self._apply_filters)
        self.in_amount_min.valueChanged.connect(lambda _: self._apply_filters())
        self.in_amount_max.valueChanged.connect(lambda _: self._apply_filters())

        filters_bar.addWidget(self.in_search)
        filters_bar.addWidget(self.cb_bank)
        filters_bar.addWidget(self.cb_type)
        filters_bar.addWidget(self.cb_duration)
        filters_bar.addWidget(self.in_amount_min)
        filters_bar.addWidget(self.in_amount_max)
        active_layout.addLayout(filters_bar)

        # Table Card
        card = QGroupBox("همه وام‌ها")
        card.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #ddd; border-radius:6px; margin-top:10px;} QGroupBox::title{subcontrol-origin: margin; subcontrol-position: top right; padding: 0 8px;}")
        card_layout = QVBoxLayout(); card_layout.setSpacing(8)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID", "بانک", "نوع", "مدت", "مبلغ", "مالک", "وضعیت", "نمایش", "ویرایش", "حذف"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(int(55))
        self.table.setStyleSheet("QTableWidget{background:white;} QHeaderView::section{background:#f8f9fa; padding:6px; border:1px solid #e9ecef;} QTableWidget::item{padding:10px;}")
        card_layout.addWidget(self.table)

        # Controls under table
        controls = QHBoxLayout()
        btn_add = QPushButton("افزودن وام")
        btn_add.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#0b5ed7}")
        btn_add.clicked.connect(self._open_add)
        btn_refresh = QPushButton("نوسازی فهرست"); btn_refresh.clicked.connect(self._load_loans)
        btn_refresh.setStyleSheet("QPushButton{background:#6c757d;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#5c636a}")
        controls.addWidget(btn_add); controls.addStretch(1); controls.addWidget(btn_refresh)
        card_layout.addLayout(controls)

        card.setLayout(card_layout)
        active_layout.addWidget(card)

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignCenter)
        active_layout.addWidget(self.lbl_status)

        # History Tab UI
        history_card = QGroupBox("سوابق وام")
        history_card.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #ddd; border-radius:6px; margin-top:10px;} QGroupBox::title{subcontrol-origin: margin; subcontrol-position: top right; padding: 0 8px;}")
        history_card_layout = QVBoxLayout(); history_card_layout.setSpacing(8)

        self.table_history = QTableWidget(0, 10)
        self.table_history.setHorizontalHeaderLabels([
            "ID", "بانک", "نوع", "مدت", "مبلغ", "مالک", "وضعیت", "نمایش", "ویرایش", "حذف"
        ])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_history.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_history.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_history.setAlternatingRowColors(True)
        self.table_history.verticalHeader().setDefaultSectionSize(int(55))
        self.table_history.setStyleSheet("QTableWidget{background:white;} QHeaderView::section{background:#f8f9fa; padding:6px; border:1px solid #e9ecef;} QTableWidget::item{padding:10px;}")
        history_card_layout.addWidget(self.table_history)

        history_controls = QHBoxLayout()
        btn_refresh_history = QPushButton("نوسازی فهرست")
        btn_refresh_history.clicked.connect(self._load_loans)
        btn_refresh_history.setStyleSheet("QPushButton{background:#6c757d;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#5c636a}")
        history_controls.addStretch(1); history_controls.addWidget(btn_refresh_history)
        history_card_layout.addLayout(history_controls)

        history_card.setLayout(history_card_layout)
        history_layout.addWidget(history_card)

        self.setLayout(layout)
        self.setStyleSheet("QWidget{background:white;color:black;}")

        self._all: List[Dict[str, Any]] = []
        self._load_loans()

    def _populate_filter_values(self):
        # Fill bank/type/duration from data
        banks, types, durations = set(), set(), set()
        for it in self._all:
            if it.get("bank_name"): banks.add(it.get("bank_name"))
            if it.get("loan_type"): types.add(it.get("loan_type"))
            if it.get("duration"): durations.add(it.get("duration"))
        def refill(cb: QComboBox, items: List[str], all_label: str):
            cur = cb.currentText()
            cb.blockSignals(True)
            cb.clear(); cb.addItem(all_label, "")
            for s in sorted(items):
                cb.addItem(s, s)
            # try keep previous selection
            idx = cb.findText(cur)
            if idx >= 0: cb.setCurrentIndex(idx)
            cb.blockSignals(False)
        refill(self.cb_bank, list(banks), "همه بانک‌ها")
        refill(self.cb_type, list(types), "همه نوع وام‌ها")
        refill(self.cb_duration, list(durations), "همه مدت‌ها")

    def _load_loans(self):
        try:
            r = api_client.get(API_LOANS)
            data = api_client.parse_json(r)
        except Exception:
            self.lbl_status.setText("بارگذاری لیست وام‌ها ناموفق بود.")
            return
        if data.get("status") == "success":
            self._all = data.get("items", [])
            self._populate_filter_values()
            self._apply_filters()
            self.lbl_status.setText("" if self._all else "رکوردی وجود ندارد.")
        else:
            self.lbl_status.setText(data.get("message", "خطا در دریافت لیست وام‌ها."))

    def _apply_filters(self):
        txt = (self.in_search.text() or "").strip().lower()
        bank = self.cb_bank.currentData()
        typ = self.cb_type.currentData()
        dur = self.cb_duration.currentData()
        min_amount = float(self.in_amount_min.value())
        max_amount = float(self.in_amount_max.value())
        def match(it: Dict[str, Any]) -> bool:
            if txt:
                name = ((it.get("bank_name") or "") + " " + (it.get("owner_full_name") or "")).lower()
                if txt not in name:
                    return False
            if bank and it.get("bank_name") != bank:
                return False
            if typ and it.get("loan_type") != typ:
                return False
            if dur and it.get("duration") != dur:
                return False
            try:
                amt = float(it.get("amount") or 0)
            except Exception:
                amt = 0
            if amt < min_amount:
                return False
            if max_amount > 0 and amt > max_amount:
                return False
            return True
        filtered = [it for it in self._all if match(it)]
        # Split into Active (not purchased) and History (purchased)
        history = [it for it in filtered if str(it.get("loan_status", "")).lower() == "purchased"]
        active = [it for it in filtered if str(it.get("loan_status", "")).lower() != "purchased"]
        self._render_active(active)
        self._render_history(history)

    def _render_active(self, items: List[Dict[str, Any]]):
        # Render Active Loans (non-purchased) in main table
        self.table.setRowCount(0)
        for it in items:
            row = self.table.rowCount(); self.table.insertRow(row)
            rid = it.get("id", "")
            self.table.setItem(row, 0, QTableWidgetItem(str(rid)))
            self.table.setItem(row, 1, QTableWidgetItem(it.get("bank_name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(it.get("loan_type", "")))
            self.table.setItem(row, 3, QTableWidgetItem(it.get("duration", "")))
            # amount formatting
            try:
                amt = float(it.get("amount") or 0); amt_txt = f"{amt:,.2f}"
            except Exception:
                amt_txt = str(it.get("amount", ""))
            item_amt = QTableWidgetItem(amt_txt)
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, item_amt)
            self.table.setItem(row, 5, QTableWidgetItem(it.get("owner_full_name", "")))
            self.table.setItem(row, 6, QTableWidgetItem(t_status(it.get("loan_status", ""))))
            # actions
            btn_view = QPushButton("نمایش"); btn_edit = QPushButton("ویرایش"); btn_del = QPushButton("حذف")
            for b, c in ((btn_view, "#198754"), (btn_edit, "#0d6efd"), (btn_del, "#dc3545")):
                b.setStyleSheet(f"QPushButton{{background:{c};color:white;padding:6px 10px;border-radius:4px;}} QPushButton:hover{{opacity:0.9}}")
            def _make_view(id_):
                return lambda: self._open_view(id_)
            def _make_edit(id_):
                return lambda: self._open_edit(id_)
            def _make_del(id_):
                return lambda: self._delete(id_)
            btn_view.clicked.connect(_make_view(rid))
            btn_edit.clicked.connect(_make_edit(rid))
            btn_del.clicked.connect(_make_del(rid))
            self.table.setCellWidget(row, 7, btn_view)
            self.table.setCellWidget(row, 8, btn_edit)
            self.table.setCellWidget(row, 9, btn_del)

    def _render_history(self, items: List[Dict[str, Any]]):
        # Render purchased loans in history table
        self.table_history.setRowCount(0)
        for it in items:
            row = self.table_history.rowCount(); self.table_history.insertRow(row)
            rid = it.get("id", "")
            self.table_history.setItem(row, 0, QTableWidgetItem(str(rid)))
            self.table_history.setItem(row, 1, QTableWidgetItem(it.get("bank_name", "")))
            self.table_history.setItem(row, 2, QTableWidgetItem(it.get("loan_type", "")))
            self.table_history.setItem(row, 3, QTableWidgetItem(it.get("duration", "")))
            # amount formatting
            try:
                amt = float(it.get("amount") or 0); amt_txt = f"{amt:,.2f}"
            except Exception:
                amt_txt = str(it.get("amount", ""))
            item_amt = QTableWidgetItem(amt_txt)
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_history.setItem(row, 4, item_amt)
            self.table_history.setItem(row, 5, QTableWidgetItem(it.get("owner_full_name", "")))
            self.table_history.setItem(row, 6, QTableWidgetItem(t_status(it.get("loan_status", ""))))
            # actions (reuse same handlers)
            btn_view = QPushButton("نمایش"); btn_edit = QPushButton("ویرایش"); btn_del = QPushButton("حذف")
            for b, c in ((btn_view, "#198754"), (btn_edit, "#0d6efd"), (btn_del, "#dc3545")):
                b.setStyleSheet(f"QPushButton{{background:{c};color:white;padding:6px 10px;border-radius:4px;}} QPushButton:hover{{opacity:0.9}}")
            def _make_view(id_):
                return lambda: self._open_view(id_)
            def _make_edit(id_):
                return lambda: self._open_edit(id_)
            def _make_del(id_):
                return lambda: self._delete(id_)
            btn_view.clicked.connect(_make_view(rid))
            btn_edit.clicked.connect(_make_edit(rid))
            btn_del.clicked.connect(_make_del(rid))
            self.table_history.setCellWidget(row, 7, btn_view)
            self.table_history.setCellWidget(row, 8, btn_edit)
            self.table_history.setCellWidget(row, 9, btn_del)

    def _open_add(self):
        dlg = LoanAddDialog(self)
        if dlg.exec():
            self._load_loans()

    def _open_edit(self, loan_id: int):
        dlg = LoanEditDialog(int(loan_id), self)
        if dlg.exec():
            self._load_loans()

    def _open_view(self, loan_id: int):
        dlg = LoanViewDialog(int(loan_id), self)
        dlg.exec()

    def _delete(self, loan_id: int):
        if delete_loan_with_confirm(self, int(loan_id)):
            self._load_loans()