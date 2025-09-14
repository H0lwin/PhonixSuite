# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt

from ..services import api_client
from ..utils.styles import PRIMARY, SECONDARY, DANGER
from ..components.loan_dialogs import LoanViewDialog  # reuse dialog styling patterns
from ..components.buyer_dialogs import BuyerAddDialog, BuyerEditDialog
from ..utils.i18n import t_status

API_BUYERS = "http://127.0.0.1:5000/api/loan-buyers"


STATUS_LABELS = [
    ("request_registered", "درخواست ثبت شد"),
    ("under_review", "در حال بررسی"),
    ("rights_transfer", "انتقال حقوق"),
    ("bank_validation", "اعتبارسنجی بانکی"),
    ("loan_paid", "وام پرداخت شد"),
    ("guarantor_issue", "ضامن ناقص"),
    ("borrower_issue", "اطلاعات وام‌گیرنده ناقص"),
]

status_label_map = dict(STATUS_LABELS)


class BuyersView(QWidget):
    def __init__(self, employee_mode=False):
        super().__init__()
        self.employee_mode = employee_mode  # Track if in employee mode
        layout = QVBoxLayout(self); layout.setSpacing(10)

        # Tabs header (Active / History) - History only for admin
        if not self.employee_mode:
            tabs = QHBoxLayout(); tabs.setSpacing(8)
            self.btn_tab_active = QPushButton("خریداران فعال")
            self.btn_tab_history = QPushButton("سوابق خریداران")
            tab_style = (
                "QPushButton{padding:6px 14px;border:1px solid #dee2e6;border-radius:8px;"
                "background:#f1f3f5;color:#212529;}"
                " QPushButton:hover{background:#e9ecef;}"
                " QPushButton:checked{background:#0d6efd;color:white;border-color:#0d6efd;}"
            )
            for b in (self.btn_tab_active, self.btn_tab_history):
                b.setCheckable(True)
                b.setStyleSheet(tab_style)
            self.btn_tab_active.setChecked(True)
            self._current_tab = "active"
            self.btn_tab_active.clicked.connect(lambda: self._switch_tab("active"))
            self.btn_tab_history.clicked.connect(lambda: self._switch_tab("history"))
            tabs.addWidget(self.btn_tab_active); tabs.addWidget(self.btn_tab_history); tabs.addStretch(1)
            layout.addLayout(tabs)
        else:
            # Employee mode: no tabs, just active buyers - Remove incorrect title
            self._current_tab = "active"

        # Search + Add button (for Active tab)
        self.top_bar = QHBoxLayout(); self.top_bar.setSpacing(8)
        self.in_search = QLineEdit(); self.in_search.setPlaceholderText("جستجو نام / کدملی / تلفن")
        self.cb_status = QComboBox(); self.cb_status.addItem("همه وضعیت‌ها", "")
        for val, fa in STATUS_LABELS:
            self.cb_status.addItem(fa, val)
        self.btn_add = QPushButton("افزودن خریدار")
        self.btn_add.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:6px 12px;border-radius:6px;} QPushButton:hover{background:#0b5ed7}")
        self.btn_add.clicked.connect(self._open_add)
        self.in_search.textChanged.connect(self._apply_filters)
        self.cb_status.currentIndexChanged.connect(self._apply_filters)
        self.top_bar.addWidget(self.in_search); self.top_bar.addWidget(self.cb_status); self.top_bar.addStretch(1); self.top_bar.addWidget(self.btn_add)
        layout.addLayout(self.top_bar)

        # Split: Left table, Right timeline
        self.split = QSplitter(Qt.Horizontal)

        left = QWidget(); left_l = QVBoxLayout(left); left_l.setSpacing(8)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["خریدار", "Loan ID", "مبلغ", "وضعیت", "ثبت‌کننده", "عملیات", "ID"])  # Active columns
        # Balanced column widths for readability
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setColumnHidden(6, True)
        left_l.addWidget(self.table)

        right = QWidget(); right_l = QVBoxLayout(right); right_l.setSpacing(8)
        grp = QGroupBox("تاریخچه وضعیت")
        grp.setStyleSheet("QGroupBox{font-weight:bold;border:1px solid #dee2e6;border-radius:8px;margin-top:6px;} QGroupBox::title{subcontrol-origin: margin;subcontrol-position: top right; padding:0 8px;}")
        grp_l = QVBoxLayout(grp); grp_l.setSpacing(6)
        self.lbl_tl_title = QLabel("تایم‌لاین وضعیت")
        self.lbl_tl_hint = QLabel("یک خریدار را از جدول انتخاب کنید تا تاریخچه وضعیت نمایش داده شود.")
        self.lbl_tl_hint.setAlignment(Qt.AlignCenter)
        self.list_timeline = QListWidget(); self.list_timeline.setVisible(False)
        self.list_timeline.setStyleSheet("QListWidget{background:white;border:none;} QListWidget::item{padding:6px 8px}")
        grp_l.addWidget(self.lbl_tl_title)
        grp_l.addWidget(self.lbl_tl_hint)
        grp_l.addWidget(self.list_timeline)
        # Reduce height proportionally
        grp.setMaximumHeight(240)
        right_l.addWidget(grp)

        self.split.addWidget(left); self.split.addWidget(right)
        # ~80% table, ~20% timeline panel (10% narrower than before)
        self.split.setStretchFactor(0, 8); self.split.setStretchFactor(1, 2)
        layout.addWidget(self.split)

        self._all: List[Dict[str, Any]] = []
        self._selected_id: Optional[int] = None
        self._load_active()

        self.table.itemSelectionChanged.connect(self._on_row_selected)

    def _reload_current_tab(self):
        if self._current_tab == "active":
            # Reset columns to active and reload
            self.table.clear()
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(["خریدار", "Loan ID", "مبلغ", "وضعیت", "ثبت‌کننده", "عملیات", "ID"])
            self.table.setColumnHidden(6, True)
            self._load_active()
        else:
            # Reset columns to history and reload
            self.table.clear()
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["خریدار", "Loan ID", "مبلغ", "تاریخ تکمیل", "ثبت‌کننده"])  # Per spec
            self._load_history()

    def _switch_tab(self, name: str):
        # Employee mode doesn't have tabs
        if self.employee_mode:
            return
            
        self._current_tab = name
        self.btn_tab_active.setChecked(name == "active")
        self.btn_tab_history.setChecked(name == "history")
        if name == "active":
            # Ensure top bar shows search + status + add
            self.cb_status.setVisible(True)
            self.btn_add.setVisible(True)
            # Reset columns for Active table every time
            self.table.clear()
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(["خریدار", "Loan ID", "مبلغ", "وضعیت", "ثبت‌کننده", "عملیات", "ID"])
            self.table.setColumnHidden(6, True)
            self._load_active()
        else:
            # Switch to History: hide status filter and add button, show only search
            self.cb_status.setVisible(False)
            self.btn_add.setVisible(False)
            # Reset columns for History table every time
            self.table.clear()
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["خریدار", "Loan ID", "مبلغ", "تاریخ تکمیل", "ثبت‌کننده"])  # Per spec
            self._load_history()

    def _load_active(self):
        try:
            r = api_client.get(API_BUYERS)
            data = r.json()
        except Exception:
            data = {"status": "error", "items": []}
        items = data.get("items", []) if data.get("status") == "success" else []
        # Active dataset = exclude completed (loan_paid)
        actives = [it for it in items if it.get("processing_status") != "loan_paid"]
        self._all = actives
        self._apply_filters()

    def _load_history(self):
        # Reuse same endpoint for now; in future backend can expose closed-only list
        try:
            r = api_client.get(API_BUYERS)
            data = r.json()
        except Exception:
            data = {"status": "error", "items": []}
        items = data.get("items", []) if data.get("status") == "success" else []
        # History dataset = only completed (loan_paid)
        hist = [it for it in items if it.get("processing_status") == "loan_paid"]
        # Render history columns: Buyer, Loan ID, Amount, Completion Date, Registered Employee
        self.table.setRowCount(0)
        for it in hist:
            row = self.table.rowCount(); self.table.insertRow(row)
            full = f"{it.get('first_name','')} {it.get('last_name','')}".strip()
            self.table.setItem(row, 0, QTableWidgetItem(full))
            self.table.setItem(row, 1, QTableWidgetItem(str(it.get("loan_id") or "-")))
            amt = it.get("requested_amount") or 0
            try:
                amt_txt = f"{float(amt):,.0f}"
            except Exception:
                amt_txt = str(amt)
            self.table.setItem(row, 2, QTableWidgetItem(amt_txt))
            # Completion date: use latest history entry date; fallback to created_at
            comp = str(it.get("updated_at", "") or it.get("created_at", ""))
            self.table.setItem(row, 3, QTableWidgetItem(comp or "-"))
            creator = it.get("created_by_name") or "-"
            self.table.setItem(row, 4, QTableWidgetItem(creator))
        # Clear timeline area in history tab
        self._selected_id = None
        self.lbl_tl_hint.setVisible(True)
        self.list_timeline.setVisible(False)


    def _apply_filters(self):
        txt = (self.in_search.text() or "").strip().lower()
        st = self.cb_status.currentData()
        def match(it: Dict[str, Any]) -> bool:
            if txt:
                hay = f"{it.get('first_name','')} {it.get('last_name','')} {it.get('national_id','')} {it.get('phone','')}".lower()
                if txt not in hay:
                    return False
            if st and it.get("processing_status") != st:
                return False
            return True
        items = [x for x in self._all if match(x)]
        # Only render in active tab; history tab uses its own renderer
        if self._current_tab == "active":
            self._render_table(items)

    def _render_table(self, items: List[Dict[str, Any]]):
        self.table.setRowCount(0)
        for it in items:
            row = self.table.rowCount(); self.table.insertRow(row)
            full = f"{it.get('first_name','')} {it.get('last_name','')}".strip()
            amt = it.get("requested_amount") or 0
            try:
                amt_txt = f"{float(amt):,.0f}"
            except Exception:
                amt_txt = str(amt)
            status = it.get("processing_status") or ""
            status_fa = t_status(status)
            badge = QLabel(status_fa)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                "QLabel{padding:4px 8px;border-radius:10px;background:" + ("#198754" if status=="loan_paid" else "#ffc107" if status=="under_review" else "#6c757d") + ";color:white;}"
            )
            creator = it.get("created_by_name") or "-"

            # Columns: Buyer, Loan ID, Amount, Status badge, Creator, Actions, hidden ID
            self.table.setItem(row, 0, QTableWidgetItem(full))
            self.table.setItem(row, 1, QTableWidgetItem(str(it.get("loan_id") or "-")))
            self.table.setItem(row, 2, QTableWidgetItem(amt_txt))
            self.table.setCellWidget(row, 3, badge)
            self.table.setItem(row, 4, QTableWidgetItem(creator))

            # Compact emoji buttons
            btn_view = QPushButton("👁")
            btn_edit = QPushButton("✏️")
            btn_del = QPushButton("🗑️")
            for b in (btn_view, btn_edit, btn_del):
                b.setFixedSize(28, 28)
                b.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
            bid = int(it.get("id"))
            btn_view.clicked.connect(lambda _, x=bid: self._open_view(x))
            btn_edit.clicked.connect(lambda _, x=bid: self._open_edit(x))
            btn_del.clicked.connect(lambda _, x=bid: self._delete_buyer(x))
            actions = QWidget(); hl = QHBoxLayout(actions); hl.setContentsMargins(0,0,0,0); hl.setSpacing(4)
            hl.addWidget(btn_view); hl.addWidget(btn_edit); hl.addWidget(btn_del); hl.addStretch(1)
            self.table.setCellWidget(row, 5, actions)
            self.table.setItem(row, 6, QTableWidgetItem(str(bid)))

    def _on_row_selected(self):
        # Only active tab has a hidden ID and timeline updates
        if self._current_tab != "active":
            return
        items = self.table.selectedItems()
        if not items:
            self._selected_id = None
            self.lbl_tl_hint.setVisible(True)
            self.list_timeline.setVisible(False)
            return
        # hidden ID is always the last column
        row = items[0].row()
        try:
            hid_col = self.table.columnCount() - 1
            self._selected_id = int(self.table.item(row, hid_col).text())
        except Exception:
            self._selected_id = None
        if self._selected_id:
            self._load_timeline(self._selected_id)

    def _load_timeline(self, buyer_id: int):
        try:
            r = api_client.get(f"{API_BUYERS}/{buyer_id}/history")
            data = r.json()
        except Exception:
            data = {"status": "error", "items": []}
        if data.get("status") == "success":
            self.lbl_tl_hint.setVisible(False)
            self.list_timeline.setVisible(True)
            self.list_timeline.clear()
            # Convert ISO/Gregorian date to Jalali for display
            from ..components.jalali_date import gregorian_to_jalali
            for it in data.get("items", []):
                status_fa = status_label_map.get(it.get("status"), it.get("status"))
                iso = str(it.get("changed_at") or "")[:10]
                try:
                    y, m, d = map(int, iso.split("-"))
                    jy, jm, jd = gregorian_to_jalali(y, m, d)
                    when = f"{jy:04d}-{jm:02d}-{jd:02d}"
                except Exception:
                    when = iso
                item = QListWidgetItem(f"{status_fa}  •  {when}")
                self.list_timeline.addItem(item)
        else:
            self.lbl_tl_hint.setVisible(True)
            self.list_timeline.setVisible(False)

    # --- Actions ---
    def _open_add(self):
        dlg = BuyerAddDialog(self)
        if dlg.exec():
            self._reload_current_tab()

    def _open_view(self, buyer_id: int):
        # Placeholder: open minimal details using API and show in a simple message dialog or a proper dialog later
        try:
            r = api_client.get(f"{API_BUYERS}/{buyer_id}")
            data = r.json()
            if data.get("status") == "success":
                item = data.get("item", {})
                from PySide6.QtWidgets import QMessageBox
                full = f"{item.get('first_name','')} {item.get('last_name','')}".strip()
                amt = item.get("requested_amount") or 0
                try:
                    amt_txt = f"{float(amt):,.0f}"
                except Exception:
                    amt_txt = str(amt)
                msg = QMessageBox(self)
                msg.setWindowTitle("جزئیات خریدار")
                msg.setText(f"نام: {full}\nکدملی: {item.get('national_id','')}\nمبلغ درخواستی: {amt_txt}")
                msg.exec()
        except Exception:
            pass

    def _open_edit(self, buyer_id: int):
        dlg = BuyerEditDialog(buyer_id, self)
        if dlg.exec():
            self._reload_current_tab()

    def _delete_buyer(self, buyer_id: int):
        from PySide6.QtWidgets import QMessageBox
        m = QMessageBox.question(self, "حذف خریدار", "آیا از حذف این خریدار اطمینان دارید؟")
        if m == QMessageBox.StandardButton.Yes:
            try:
                r = api_client.delete(f"{API_BUYERS}/{buyer_id}")
                data = r.json()
                if data.get("status") == "success":
                    self._reload_current_tab()
            except Exception:
                pass