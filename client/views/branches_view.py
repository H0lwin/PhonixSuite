# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGroupBox, QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt

from ..services import api_client
from ..utils.styles import PRIMARY, PRIMARY_HOVER, SECONDARY, SECONDARY_HOVER, DANGER

API_BRANCHES = "http://127.0.0.1:5000/api/branches"
API_EMP_META = "http://127.0.0.1:5000/api/employees/meta"


class BranchAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن شعبه")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_name = QLineEdit(); self.in_name.setPlaceholderText("مثال: Main Branch")
        self.in_loc = QLineEdit(); self.in_loc.setPlaceholderText("مثال: Tehran, Iran")
        self.cb_manager = QComboBox(); self._load_active_employees()

        form.addRow("نام شعبه", self.in_name)
        form.addRow("موقعیت", self.in_loc)
        form.addRow("مدیر شعبه", self.cb_manager)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_active_employees(self):
        try:
            r = api_client.get(API_EMP_META)
            data = api_client.parse_json(r)
        except Exception:
            data = {}
        self.cb_manager.clear()
        self.cb_manager.addItem("بدون مدیر", None)
        # We need all employees to filter active; meta endpoint returns only deps/branches.
        # As a workaround, we can fetch employees list and filter active here if needed.
        try:
            r2 = api_client.get("http://127.0.0.1:5000/api/employees")
            d2 = api_client.parse_json(r2)
            if d2.get("status") == "success":
                for it in d2.get("items", []):
                    if (it.get("status") or "") == "active":
                        self.cb_manager.addItem(it.get("full_name", "-"), it.get("id"))
        except Exception:
            pass

    def _submit(self):
        name = (self.in_name.text() or "").strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام شعبه الزامی است.")
            return
        payload = {
            "name": name,
            "location": (self.in_loc.text() or "").strip(),
            "manager_id": self.cb_manager.currentData(),
        }
        try:
            r = api_client.post_json(API_BRANCHES, payload)
            data = api_client.parse_json(r)
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "ثبت ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "ثبت ناموفق بود.")


class BranchesView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(); layout.setSpacing(12)

        # Header (Farsi, modern card style)
        title = QLabel("مدیریت شعب")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#212529;")
        desc = QLabel("مدیریت شعب سازمان و کارمندان تخصیص‌داده‌شده به هر شعبه")
        desc.setStyleSheet("color:#6c757d;margin-bottom:6px;")
        layout.addWidget(title); layout.addWidget(desc)

        # Connect to global signals for auto-refresh
        try:
            from ..main import global_signals
            global_signals.employee_updated.connect(self._load)
        except Exception:
            pass

        # Top bar: Add + Refresh (right aligned, consistent style)
        bar = QHBoxLayout(); bar.setSpacing(8)
        btn_add = QPushButton("افزودن شعبه")
        btn_add.setStyleSheet(
            "QPushButton{background:%s;color:white;padding:6px 12px;border-radius:8px;} QPushButton:hover{background:%s}" % (PRIMARY, PRIMARY_HOVER)
        )
        btn_add.clicked.connect(self._open_add)
        btn_refresh = QPushButton("نوسازی")
        btn_refresh.setStyleSheet(
            "QPushButton{background:%s;color:white;padding:6px 12px;border-radius:8px;} QPushButton:hover{background:%s}" % (SECONDARY, SECONDARY_HOVER)
        )
        btn_refresh.clicked.connect(self._load)
        bar.addStretch(1); bar.addWidget(btn_refresh); bar.addWidget(btn_add)
        layout.addLayout(bar)

        # Branch Table card
        from PySide6.QtWidgets import QGroupBox
        card = QGroupBox("فهرست شعب")
        card.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #dee2e6; border-radius:10px; margin-top:10px;} QGroupBox::title{subcontrol-origin: margin; subcontrol-position: top right; padding: 0 10px;}")
        card_layout = QVBoxLayout(); card_layout.setSpacing(8)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["نام شعبه", "موقعیت", "تعداد کارمندان", "کارمندان", "حذف"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setStyleSheet("QTableWidget{background:white;} QHeaderView::section{background:#f8f9fa; padding:8px; border:1px solid #e9ecef;} QTableWidget::item{padding:8px;}")
        card_layout.addWidget(self.table)
        card.setLayout(card_layout)
        layout.addWidget(card)

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        self.setLayout(layout)
        self.setStyleSheet("QWidget{background:white;color:black;}")
        self._items: List[Dict[str, Any]] = []
        self._load()

    def _open_add(self):
        dlg = BranchAddDialog(self)
        if dlg.exec():
            self._load()

    def _load(self):
        try:
            r = api_client.get(API_BRANCHES)
            data = api_client.parse_json(r)
        except Exception:
            data = {"status": "error"}
        if data.get("status") == "success":
            self._items = data.get("items", [])
            self._render()
            self.lbl_status.setText("" if self._items else "رکوردی وجود ندارد.")
        else:
            self._items = []
            self._render()
            self.lbl_status.setText(data.get("message", "بارگذاری شعب ناموفق بود."))

    def _render(self):
        self.table.setRowCount(0)
        for it in self._items:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(it.get("name", "")))
            self.table.setItem(r, 1, QTableWidgetItem(it.get("location", "")))
            self.table.setItem(r, 2, QTableWidgetItem(str(it.get("employee_count") or 0)))
            # View Employees button
            btn_view = QPushButton("مشاهده کارمندان")
            btn_view.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:4px 10px;border-radius:6px;} QPushButton:hover{background:#0b5ed7}")
            bid = int(it.get("id"))
            btn_view.clicked.connect(lambda _, x=bid: self._view_employees(x))
            self.table.setCellWidget(r, 3, btn_view)
            # Delete button
            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(32, 28)
            btn_del.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
            btn_del.clicked.connect(lambda _, x=bid: self._delete_branch(x))
            self.table.setCellWidget(r, 4, btn_del)

    def _view_employees(self, branch_id: int):
        try:
            r = api_client.get(f"{API_BRANCHES}/{branch_id}/employees")
            data = api_client.parse_json(r)
        except Exception:
            data = {"status": "error", "items": []}
        if data.get("status") != "success":
            QMessageBox.warning(self, "خطا", data.get("message", "دریافت کارمندان ناموفق بود."))
            return
        items = data.get("items", [])

        # Beautiful structured dialog: title, subtitle, table, totals, close
        dlg = QDialog(self)
        dlg.setWindowTitle("کارمندان این شعبه")
        dlg.setModal(True)
        dlg.setMinimumWidth(560)
        lay = QVBoxLayout(dlg); lay.setSpacing(10)

        title = QLabel("فهرست کارمندان")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#212529;")
        subtitle = QLabel("نام، نقش و وضعیت هر کارمند این شعبه")
        subtitle.setStyleSheet("color:#6c757d;")
        lay.addWidget(title); lay.addWidget(subtitle)

        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        tbl = QTableWidget(0, 4)
        tbl.setHorizontalHeaderLabels(["ID", "نام کامل", "نقش", "وضعیت"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(36)
        tbl.setStyleSheet("QTableWidget{background:white;} QHeaderView::section{background:#f8f9fa; padding:8px; border:1px solid #e9ecef;} QTableWidget::item{padding:8px;}")

        for it in items:
            r = tbl.rowCount(); tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(str(it.get("id", ""))))
            tbl.setItem(r, 1, QTableWidgetItem(it.get("full_name", "")))
            tbl.setItem(r, 2, QTableWidgetItem(it.get("role", "")))
            # Localized status pill
            from ..utils.i18n import t_status
            val = (it.get("status") or "")
            badge = QLabel(t_status(val)); badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                "QLabel{padding:4px 10px;border-radius:999px;background:" + ("#198754" if val=="active" else "#6c757d") + ";color:white;}"
            )
            tbl.setCellWidget(r, 3, badge)
        lay.addWidget(tbl)

        # Totals / footer
        cnt = len(items)
        footer = QLabel(f"تعداد کارمندان: {cnt}")
        footer.setStyleSheet("color:#495057;")
        lay.addWidget(footer)

        # Close button styled
        from ..utils.styles import style_dialog_buttons
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        style_dialog_buttons(btns)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        dlg.exec()

    def _delete_branch(self, branch_id: int):
        from PySide6.QtWidgets import QMessageBox
        m = QMessageBox.question(self, "حذف شعبه", "آیا از حذف این شعبه اطمینان دارید؟")
        if m == QMessageBox.StandardButton.Yes:
            try:
                r = api_client.delete(f"{API_BRANCHES}/{branch_id}")
                data = api_client.parse_json(r)
                if data.get("status") == "success":
                    self._load()
                else:
                    QMessageBox.warning(self, "خطا", data.get("message", "حذف ناموفق بود."))
            except Exception:
                QMessageBox.critical(self, "خطا", "حذف ناموفق بود.")