# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox, QAbstractSpinBox,
    QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, QLocale

# Local API client (injects token)
from ..services import api_client
from ..utils.styles import style_dialog_buttons

API_EMP_META = "http://127.0.0.1:5000/api/employees/meta"
API_EMP = "http://127.0.0.1:5000/api/employees"


def _load_meta() -> Dict[str, Any]:
    r = api_client.get(API_EMP_META)
    data = r.json()
    # Support both plain payload (no status) and wrapped success payloads
    if isinstance(data, dict) and "branches" in data:
        return data
    if data.get("status") == "success":
        return data
    raise RuntimeError(data.get("message", "Failed to load meta"))


def _load_employee(emp_id: int) -> Dict[str, Any]:
    r = api_client.get(f"{API_EMP}/{emp_id}")
    data = r.json()
    if isinstance(data, dict) and ("item" in data or "id" in data):
        return data.get("item", data)
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "Failed to load employee"))
    return data.get("item", {})


class EmployeeAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن کارمند")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._meta = _load_meta()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.in_full_name = QLineEdit(); self.in_full_name.setPlaceholderText("مثال: علی مرادی")
        self.in_national_id = QLineEdit(); self.in_national_id.setPlaceholderText("کد ملی ۱۰ رقمی")
        self.in_password = QLineEdit(); self.in_password.setEchoMode(QLineEdit.Password); self.in_password.setPlaceholderText("رمز عبور")
        self.in_role = QLineEdit(); self.in_role.setPlaceholderText("مثال: کارشناس وام")

        self.cb_branch = QComboBox()
        # Populate branches dynamically from server meta
        for b in self._meta.get("branches", []):
            self.cb_branch.addItem(b.get("name", ""), b.get("id"))

        self.in_phone = QLineEdit(); self.in_phone.setPlaceholderText("مثال: ۰۹۱۲۳۴۵۶۷۸۹")
        self.in_address = QTextEdit(); self.in_address.setPlaceholderText("مثال: تهران، خیابان اصلی، پلاک ۱۲۳")

        self.in_salary = QDoubleSpinBox(); self.in_salary.setRange(0, 10_000_000_000); self.in_salary.setDecimals(0)
        # Remove spin buttons, add thousand separators, align right
        self.in_salary.setLocale(QLocale(QLocale.English))
        self.in_salary.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_salary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_salary.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        self.cb_status = QComboBox(); self.cb_status.addItems(["فعال", "غیرفعال"]) 

        form.addRow("نام و نام خانوادگی", self.in_full_name)
        form.addRow("کد ملی (نام کاربری)", self.in_national_id)
        form.addRow("رمز عبور", self.in_password)
        form.addRow("نقش", self.in_role)
        form.addRow("شعبه", self.cb_branch)
        form.addRow("شماره تماس", self.in_phone)
        form.addRow("آدرس", self.in_address)
        form.addRow("حقوق ماهانه", self.in_salary)
        form.addRow("وضعیت", self.cb_status)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "full_name": self.in_full_name.text().strip(),
            "national_id": self.in_national_id.text().strip(),
            "password": self.in_password.text().strip(),
            "role": self.in_role.text().strip(),
            "branch_id": self.cb_branch.currentData(),
            "phone": self.in_phone.text().strip(),
            "address": self.in_address.toPlainText().strip(),
            "monthly_salary": float(self.in_salary.value()),
            "status": "active" if self.cb_status.currentIndex() == 0 else "inactive",
        }
        try:
            r = api_client.post_json(API_EMP, payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "ثبت کاربر ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "ثبت کاربر ناموفق بود.")


class EmployeeEditDialog(QDialog):
    def __init__(self, emp_id: int, parent=None):
        super().__init__(parent)
        self.emp_id = emp_id
        self.setWindowTitle("ویرایش کارمند")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._meta = _load_meta()
        self._item = _load_employee(emp_id)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_full_name = QLineEdit(self._item.get("full_name", ""))
        self.in_role = QLineEdit(self._item.get("role", ""))
        self.cb_branch = QComboBox();
        # Populate branches dynamically from server meta
        for b in self._meta.get("branches", []):
            self.cb_branch.addItem(b.get("name", ""), b.get("id"))
        if self._item.get("branch_id") is not None:
            idx = self.cb_branch.findData(self._item.get("branch_id"));
            if idx >= 0: self.cb_branch.setCurrentIndex(idx)

        self.in_phone = QLineEdit(self._item.get("phone", ""))
        self.in_address = QTextEdit(self._item.get("address", ""))
        self.in_salary = QDoubleSpinBox(); self.in_salary.setRange(0, 10_000_000_000); self.in_salary.setDecimals(0)
        # Remove spin buttons, add thousand separators, align right
        self.in_salary.setLocale(QLocale(QLocale.English))
        self.in_salary.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_salary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_salary.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        try:
            self.in_salary.setValue(float(self._item.get("monthly_salary") or 0))
        except Exception:
            self.in_salary.setValue(0)
        self.cb_status = QComboBox(); self.cb_status.addItems(["فعال", "غیرفعال"]) 
        if (self._item.get("status") or "active") == "active":
            self.cb_status.setCurrentIndex(0)
        else:
            self.cb_status.setCurrentIndex(1)

        # Optional: Password update
        self.in_password = QLineEdit(); self.in_password.setEchoMode(QLineEdit.Password); self.in_password.setPlaceholderText("رمز عبور جدید (اختیاری)")

        form.addRow("نام و نام خانوادگی", self.in_full_name)
        form.addRow("نقش", self.in_role)
        form.addRow("شعبه", self.cb_branch)
        form.addRow("شماره تماس", self.in_phone)
        form.addRow("آدرس", self.in_address)
        form.addRow("حقوق ماهانه", self.in_salary)
        form.addRow("وضعیت", self.cb_status)
        form.addRow("رمز عبور", self.in_password)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload: Dict[str, Any] = {
            "full_name": self.in_full_name.text().strip(),
            "role": self.in_role.text().strip(),
            "branch_id": self.cb_branch.currentData(),
            "phone": self.in_phone.text().strip(),
            "address": self.in_address.toPlainText().strip(),
            "monthly_salary": float(self.in_salary.value()),
            "status": "active" if self.cb_status.currentIndex() == 0 else "inactive",
        }
        pwd = self.in_password.text().strip()
        if pwd:
            payload["password"] = pwd
        try:
            r = api_client.patch_json(f"{API_EMP}/{self.emp_id}", payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "بروزرسانی ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "بروزرسانی ناموفق بود.")


class EmployeeViewDialog(QDialog):
    def __init__(self, emp_id: int, parent=None):
        super().__init__(parent)
        self.emp_id = emp_id
        self.setWindowTitle("مشاهده کارمند | View Employee")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._item = _load_employee(emp_id)
        # Load meta for mapping IDs to names
        try:
            self._meta = _load_meta()
        except Exception:
            self._meta = {"branches": []}
        br_map = {b.get("id"): b.get("name", "-") for b in self._meta.get("branches", [])}
        br_name = br_map.get(self._item.get("branch_id")) or "-"
        # Format salary nicely
        try:
            salary_val = float(self._item.get("monthly_salary") or 0)
            salary_fmt = f"{salary_val:,.0f}"
        except Exception:
            salary_fmt = str(self._item.get("monthly_salary", ""))

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight); form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18); form.setVerticalSpacing(10)

        def add_row(label_fa: str, value: str, label_en: Optional[str] = None, selectable: bool = True):
            # RTL row: label (with colon) + optional EN note + value; all RTL-aligned
            row = QWidget(); hl = QHBoxLayout(row); hl.setContentsMargins(0,0,0,0); hl.setSpacing(8)
            lbl_text = label_fa + ":"
            if label_en:
                lbl_text = lbl_text + f"  |  <span style='color:#6c757d;font-size:11px'>{label_en}</span>"
            lbl = QLabel(lbl_text); lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-weight:600; color:#212529;")
            val = QLabel(value or "-")
            if selectable:
                val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setWordWrap(True)
            lbl.setLayoutDirection(Qt.RightToLeft)
            val.setLayoutDirection(Qt.RightToLeft)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            hl.addWidget(lbl, 0)
            hl.addWidget(val, 1)
            form.addRow(row)

        add_row("شناسه", str(self._item.get("id", "")), "ID")
        add_row("نام و نام خانوادگی", self._item.get("full_name", ""), "Full Name")
        add_row("کدملی", self._item.get("national_id", ""), "National ID")
        add_row("نقش", self._item.get("role", ""), "Role")
        add_row("شعبه", br_name, "Branch")
        add_row("شماره تماس", self._item.get("phone", ""), "Phone")
        add_row("آدرس", self._item.get("address", ""), "Address")
        add_row("حقوق ماهانه", salary_fmt, "Monthly Salary")
        add_row("وضعیت", self._item.get("status", ""), "Status")

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        style_dialog_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setStyleSheet(
            """
            QDialog{background:#ffffff;}
            QLabel{font-size:13px;}
            QDialog QPushButton{min-width:100px;padding:6px 12px;}
            """
        )


def delete_employee_with_confirm(parent, emp_id: int) -> bool:
    m = QMessageBox.question(parent, "حذف کاربر", "آیا از حذف این کاربر اطمینان دارید؟")
    if m == QMessageBox.StandardButton.Yes:
        try:
            r = api_client.delete(f"{API_EMP}/{emp_id}")
            data = r.json()
            if data.get("status") == "success":
                return True
            QMessageBox.warning(parent, "خطا", data.get("message", "حذف ناموفق بود."))
        except Exception:
            QMessageBox.critical(parent, "خطا", "حذف ناموفق بود.")
    return False