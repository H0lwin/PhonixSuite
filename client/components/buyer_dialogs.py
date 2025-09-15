# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QDoubleSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QLocale

from client.services import api_client
from client.utils.styles import style_dialog_buttons

API_BUYERS = "/api/loan-buyers"
API_LOANS = "/api/loans"

STATUS_OPTIONS: List[tuple[str, str]] = [
    ("request_registered", "درخواست ثبت شد"),
    ("under_review", "در حال بررسی"),
    ("rights_transfer", "انتقال حقوق"),
    ("bank_validation", "اعتبارسنجی بانکی"),
    ("loan_paid", "وام پرداخت شد"),
    ("guarantor_issue", "ضامن ناقص"),
    ("borrower_issue", "اطلاعات وام‌گیرنده ناقص"),
]

status_to_index = {k: i for i, (k, _) in enumerate(STATUS_OPTIONS)}


def _load_loans() -> List[Dict[str, Any]]:
    try:
        r = api_client.get(API_LOANS)
        data = api_client.parse_json(r)
        if data.get("status") == "success":
            items = data.get("items", [])
            # Only show loans with status available
            return [it for it in items if (it.get("loan_status") or "").lower() == "available"]
    except Exception:
        pass
    return []


def _fmt_amount_box(decimals: int = 0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0, 10_000_000_000)
    box.setDecimals(decimals)
    box.setLocale(QLocale(QLocale.English))  # grouping + dot decimals
    box.setButtonSymbols(QDoubleSpinBox.NoButtons)  # no steppers
    box.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    box.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
    return box


class BuyerAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن خریدار جدید")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight); form.setFormAlignment(Qt.AlignTop)

        self.in_first = QLineEdit(); self.in_first.setPlaceholderText("مثال: علی")
        self.in_last = QLineEdit(); self.in_last.setPlaceholderText("مثال: مرادی")
        self.in_nid = QLineEdit(); self.in_nid.setPlaceholderText("کدملی")
        self.in_phone = QLineEdit(); self.in_phone.setPlaceholderText("مثال: 09123456789")
        self.in_amount = _fmt_amount_box(0)
        self.in_bank = QLineEdit(); self.in_bank.setPlaceholderText("بانک")
        from client.components.jalali_date import JalaliDateEdit
        self.in_visit = JalaliDateEdit(); self.in_visit.set_from_gregorian(QDate.currentDate())
        self.in_visit.setStyleSheet("QLineEdit{padding:8px 10px; border:1px solid #ced4da; border-radius:6px; font-size:13px;} QPushButton{padding:6px 10px;}")
        self.cb_loan = QComboBox()
        self._loans = _load_loans()
        self.cb_loan.addItem("بدون انتخاب", None)
        for it in self._loans:
            disp = f"#{it.get('id')} - {it.get('bank_name','')} - {it.get('owner_full_name','')}"
            self.cb_loan.addItem(disp, it.get("id"))
        self.in_sale_price = _fmt_amount_box(0)
        self.cb_sale_type = QComboBox();
        self.cb_sale_type.addItem("نقدی", "cash")
        self.cb_sale_type.addItem("شرایطی", "installment")
        self.cb_status = QComboBox()
        for val, fa in STATUS_OPTIONS:
            self.cb_status.addItem(fa, val)
        self.cb_status.setCurrentIndex(status_to_index.get("request_registered", 0))

        # Add fields with colon in labels
        form.addRow("نام: ", self.in_first)
        form.addRow("نام خانوادگی: ", self.in_last)
        form.addRow("کدملی: ", self.in_nid)
        form.addRow("تلفن: ", self.in_phone)
        form.addRow("مبلغ درخواستی: ", self.in_amount)
        form.addRow("بانک: ", self.in_bank)
        form.addRow("تاریخ بازدید: ", self.in_visit)
        form.addRow("وام هدف: ", self.cb_loan)
        form.addRow("قیمت فروش: ", self.in_sale_price)
        form.addRow("نوع فروش: ", self.cb_sale_type)
        form.addRow("وضعیت پردازش: ", self.cb_status)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "first_name": self.in_first.text().strip(),
            "last_name": self.in_last.text().strip(),
            "national_id": self.in_nid.text().strip(),
            "phone": self.in_phone.text().strip(),
            "requested_amount": float(self.in_amount.value()),
            "bank_agent": self.in_bank.text().strip(),
            "visit_date": self.in_visit.get_gregorian_iso(),
            "processing_status": self.cb_status.currentData() or "request_registered",
            "loan_id": self.cb_loan.currentData(),
            "sale_price": float(self.in_sale_price.value()),
            "sale_type": (self.cb_sale_type.currentData() or "cash"),
        }
        try:
            r = api_client.post_json(API_BUYERS, payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "ثبت خریدار ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "ثبت خریدار ناموفق بود.")


class BuyerEditDialog(QDialog):
    def __init__(self, buyer_id: int, parent=None):
        super().__init__(parent)
        self.buyer_id = buyer_id
        self.setWindowTitle("ویرایش خریدار")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setLayoutDirection(Qt.RightToLeft)

        # Load item
        try:
            r = api_client.get(f"{API_BUYERS}/{buyer_id}")
            res = r.json()
            if res.get("status") != "success":
                raise RuntimeError(res.get("message", "not found"))
            self._item = res.get("item", {})
        except Exception:
            self._item = {}

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight); form.setFormAlignment(Qt.AlignTop)

        self.in_first = QLineEdit(self._item.get("first_name", ""))
        self.in_last = QLineEdit(self._item.get("last_name", ""))
        self.in_nid = QLineEdit(self._item.get("national_id", ""))
        self.in_phone = QLineEdit(self._item.get("phone", ""))
        self.in_amount = _fmt_amount_box(0)
        try:
            self.in_amount.setValue(float(self._item.get("requested_amount") or 0))
        except Exception:
            self.in_amount.setValue(0)
        self.in_bank = QLineEdit(self._item.get("bank_agent", ""))
        from client.components.jalali_date import JalaliDateEdit
        self.in_visit = JalaliDateEdit()
        try:
            if self._item.get("visit_date"):
                self.in_visit.set_from_gregorian_str(str(self._item["visit_date"]))
            else:
                self.in_visit.set_from_gregorian(QDate.currentDate())
        except Exception:
            self.in_visit.set_from_gregorian(QDate.currentDate())
        self.in_visit.setStyleSheet("QLineEdit{padding:8px 10px; border:1px solid #ced4da; border-radius:6px; font-size:13px;} QPushButton{padding:6px 10px;}")

        self.cb_loan = QComboBox()
        self._loans = _load_loans()
        self.cb_loan.addItem("بدون انتخاب", None)
        for it in self._loans:
            disp = f"#{it.get('id')} - {it.get('bank_name','')} - {it.get('owner_full_name','')}"
            self.cb_loan.addItem(disp, it.get("id"))
        # Set current loan id
        lid = self._item.get("loan_id")
        if lid is not None:
            idx = self.cb_loan.findData(lid)
            if idx >= 0:
                self.cb_loan.setCurrentIndex(idx)

        self.in_sale_price = _fmt_amount_box(0)
        try:
            self.in_sale_price.setValue(float(self._item.get("sale_price") or 0))
        except Exception:
            self.in_sale_price.setValue(0)
        self.cb_sale_type = QComboBox();
        self.cb_sale_type.addItem("نقدی", "cash")
        self.cb_sale_type.addItem("شرایطی", "installment")
        self.cb_status = QComboBox()
        for val, fa in STATUS_OPTIONS:
            self.cb_status.addItem(fa, val)
        self.cb_status.setCurrentIndex(status_to_index.get(self._item.get("processing_status", "request_registered"), 0))

        form.addRow("نام: ", self.in_first)
        form.addRow("نام خانوادگی: ", self.in_last)
        form.addRow("کدملی: ", self.in_nid)
        form.addRow("تلفن: ", self.in_phone)
        form.addRow("مبلغ درخواستی: ", self.in_amount)
        form.addRow("بانک: ", self.in_bank)
        form.addRow("تاریخ بازدید: ", self.in_visit)
        form.addRow("وام هدف: ", self.cb_loan)
        form.addRow("قیمت فروش: ", self.in_sale_price)
        form.addRow("نوع فروش: ", self.cb_sale_type)
        form.addRow("وضعیت پردازش: ", self.cb_status)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload: Dict[str, Any] = {
            "first_name": self.in_first.text().strip(),
            "last_name": self.in_last.text().strip(),
            "national_id": self.in_nid.text().strip(),
            "phone": self.in_phone.text().strip(),
            "requested_amount": float(self.in_amount.value()),
            "bank_agent": self.in_bank.text().strip(),
            "visit_date": self.in_visit.get_gregorian_iso(),
            "processing_status": self.cb_status.currentData() or "request_registered",
            "loan_id": self.cb_loan.currentData(),
            "sale_price": float(self.in_sale_price.value()),
            "sale_type": (self.cb_sale_type.currentData() or "cash"),
        }
        try:
            r = api_client.patch_json(f"{API_BUYERS}/{self.buyer_id}", payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "بروزرسانی خریدار ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "بروزرسانی خریدار ناموفق بود.")