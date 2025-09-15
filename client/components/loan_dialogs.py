# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox, QDateEdit, QAbstractSpinBox,
    QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, QDate, QLocale

# Local API client (injects token)
from client.services import api_client
from client.utils.styles import style_dialog_buttons

API_LOANS = "/api/loans"


def _status_to_value(index: int) -> str:
    return ["available", "failed", "purchased"][index]


def _value_to_status(value: str) -> int:
    value = (value or "").lower()
    mapping = {"available": 0, "failed": 1, "purchased": 2}
    return mapping.get(value, 0)


def _format_date_for_api(qdate: QDate) -> Optional[str]:
    if not qdate or not qdate.isValid():
        return None
    return qdate.toString("yyyy-MM-dd")


def _load_loan(loan_id: int) -> Dict[str, Any]:
    r = api_client.get(f"{API_LOANS}/{loan_id}")
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "Failed to load loan"))
    return data.get("item", {})


class LoanAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن وام")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_bank_name = QLineEdit(); self.in_bank_name.setPlaceholderText("مثال: بانک سرمایه")
        # Editable Persian loan types (typed freely); value saved as typed text
        self.cb_loan_type = QComboBox(); self.cb_loan_type.setEditable(True); self.cb_loan_type.addItems(["شخصی", "مسکن", "خودرو", "کسب‌وکار"])  # editable suggestions
        self.in_duration = QLineEdit(); self.in_duration.setPlaceholderText("مثال: 24 ماه")
        self.in_amount = QDoubleSpinBox(); self.in_amount.setRange(0, 10_000_000_000); self.in_amount.setDecimals(2)
        self.in_amount.setLocale(QLocale(QLocale.English))
        self.in_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_amount.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        self.in_owner = QLineEdit(); self.in_owner.setPlaceholderText("مثال: علی مرادی")
        self.in_phone = QLineEdit(); self.in_phone.setPlaceholderText("مثال: 09123456789")
        from client.components.jalali_date import JalaliDateEdit
        self.in_visit_date = JalaliDateEdit()
        self.in_visit_date.set_from_gregorian(QDate.currentDate())
        # Larger, styled date field
        self.in_visit_date.setStyleSheet("QLineEdit{padding:8px 10px; border:1px solid #ced4da; border-radius:6px; font-size:13px;} QPushButton{padding:6px 10px;}")
        # وضعیت وام با نمایش فارسی و مقدار انگلیسی برای ذخیره
        self.cb_status = QComboBox();
        self.cb_status.addItem("🟢 موجود", "available")
        self.cb_status.addItem("❌ ناموفق", "failed")
        self.cb_status.addItem("🔴 خریداری شده", "purchased")
        self.in_referrer = QLineEdit(); self.in_referrer.setPlaceholderText("مثال: رضا قاسمی")
        # نوع پرداخت: تایپی با پیشنهادهای فارسی (حذف گزینه کارت)
        self.cb_payment_type = QComboBox(); self.cb_payment_type.setEditable(True); self.cb_payment_type.addItems(["نقدی", "اقساطی"])  # editable suggestions
        # نرخ خرید: تومان، بدون اعشار
        self.in_purchase_rate = QDoubleSpinBox(); self.in_purchase_rate.setRange(0, 1_000_000_000); self.in_purchase_rate.setDecimals(0); self.in_purchase_rate.setSuffix(" تومان")
        self.in_purchase_rate.setLocale(QLocale(QLocale.English))
        self.in_purchase_rate.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_purchase_rate.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_purchase_rate.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")

        form.addRow("نام بانک", self.in_bank_name)
        form.addRow("نوع وام", self.cb_loan_type)
        form.addRow("مدت", self.in_duration)
        form.addRow("مبلغ", self.in_amount)
        form.addRow("نام مالک", self.in_owner)
        form.addRow("تلفن", self.in_phone)
        form.addRow("تاریخ بازدید", self.in_visit_date)
        form.addRow("وضعیت وام", self.cb_status)
        form.addRow("معرف", self.in_referrer)
        form.addRow("نوع پرداخت", self.cb_payment_type)
        form.addRow("نرخ خرید", self.in_purchase_rate)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "bank_name": self.in_bank_name.text().strip(),
            "loan_type": self.cb_loan_type.currentText().strip(),
            "duration": self.in_duration.text().strip(),
            "amount": float(self.in_amount.value()),
            "owner_full_name": self.in_owner.text().strip(),
            "owner_phone": self.in_phone.text().strip(),
            "visit_date": (self.in_visit_date.get_gregorian_iso()),
            "loan_status": _status_to_value(self.cb_status.currentIndex()),
            "introducer": self.in_referrer.text().strip(),
            "payment_type": self.cb_payment_type.currentText().strip(),
            "purchase_rate": float(self.in_purchase_rate.value()),
        }
        try:
            r = api_client.post_json(API_LOANS, payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "ثبت وام ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "ثبت وام ناموفق بود.")


class LoanEditDialog(QDialog):
    def __init__(self, loan_id: int, parent=None):
        super().__init__(parent)
        self.loan_id = loan_id
        self.setWindowTitle("ویرایش وام")
        self.setModal(True)
        self.setMinimumWidth(460)

        self._item = _load_loan(loan_id)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_bank_name = QLineEdit(self._item.get("bank_name", ""))
        # Editable Persian loan types (typed freely); value saved as typed text
        self.cb_loan_type = QComboBox(); self.cb_loan_type.setEditable(True); self.cb_loan_type.addItems(["شخصی", "مسکن", "خودرو", "کسب‌وکار"])  # editable suggestions
        idx = self.cb_loan_type.findText(self._item.get("loan_type", ""))
        if idx >= 0: self.cb_loan_type.setCurrentIndex(idx)
        self.in_duration = QLineEdit(self._item.get("duration", ""))
        self.in_amount = QDoubleSpinBox(); self.in_amount.setRange(0, 10_000_000_000); self.in_amount.setDecimals(2)
        self.in_amount.setLocale(QLocale(QLocale.English))
        self.in_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_amount.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        try:
            self.in_amount.setValue(float(self._item.get("amount") or 0))
        except Exception:
            self.in_amount.setValue(0)
        self.in_owner = QLineEdit(self._item.get("owner_full_name", ""))
        self.in_phone = QLineEdit(self._item.get("owner_phone", ""))
        from client.components.jalali_date import JalaliDateEdit
        self.in_visit_date = JalaliDateEdit()
        try:
            if self._item.get("visit_date"):
                self.in_visit_date.set_from_gregorian_str(str(self._item["visit_date"]))
            else:
                self.in_visit_date.set_from_gregorian(QDate.currentDate())
        except Exception:
            self.in_visit_date.set_from_gregorian(QDate.currentDate())
        # Larger, styled date field
        self.in_visit_date.setStyleSheet("QLineEdit{padding:8px 10px; border:1px solid #ced4da; border-radius:6px; font-size:13px;} QPushButton{padding:6px 10px;}")
        self.cb_status = QComboBox();
        self.cb_status.addItem("🟢 موجود", "available")
        self.cb_status.addItem("❌ ناموفق", "failed")
        self.cb_status.addItem("🔴 خریداری شده", "purchased") 
        self.cb_status.setCurrentIndex(_value_to_status(self._item.get("loan_status")))
        self.in_referrer = QLineEdit(self._item.get("introducer", ""))
        # نوع پرداخت: تایپی با پیشنهادهای فارسی
        self.cb_payment_type = QComboBox(); self.cb_payment_type.setEditable(True); self.cb_payment_type.addItems(["نقدی", "اقساطی", "کارت"])  # editable suggestions
        idx = self.cb_payment_type.findText(self._item.get("payment_type", ""))
        if idx >= 0: self.cb_payment_type.setCurrentIndex(idx)
        # نرخ خرید: تومان، بدون اعشار
        self.in_purchase_rate = QDoubleSpinBox(); self.in_purchase_rate.setRange(0, 1_000_000_000); self.in_purchase_rate.setDecimals(0); self.in_purchase_rate.setSuffix(" تومان")
        self.in_purchase_rate.setLocale(QLocale(QLocale.English))
        self.in_purchase_rate.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_purchase_rate.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_purchase_rate.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        try:
            self.in_purchase_rate.setValue(float(self._item.get("purchase_rate") or 0))
        except Exception:
            self.in_purchase_rate.setValue(0)

        form.addRow("نام بانک", self.in_bank_name)
        form.addRow("نوع وام", self.cb_loan_type)
        form.addRow("مدت", self.in_duration)
        form.addRow("مبلغ", self.in_amount)
        form.addRow("نام مالک", self.in_owner)
        form.addRow("تلفن", self.in_phone)
        form.addRow("تاریخ بازدید", self.in_visit_date)
        form.addRow("وضعیت وام", self.cb_status)
        form.addRow("معرف", self.in_referrer)
        form.addRow("نوع پرداخت", self.cb_payment_type)
        form.addRow("نرخ خرید", self.in_purchase_rate)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "bank_name": self.in_bank_name.text().strip(),
            "loan_type": self.cb_loan_type.currentText().strip(),
            "duration": self.in_duration.text().strip(),
            "amount": float(self.in_amount.value()),
            "owner_full_name": self.in_owner.text().strip(),
            "owner_phone": self.in_phone.text().strip(),
            "visit_date": (self.in_visit_date.get_gregorian_iso()),
            "loan_status": _status_to_value(self.cb_status.currentIndex()),
            "introducer": self.in_referrer.text().strip(),
            "payment_type": self.cb_payment_type.currentText().strip(),
            "purchase_rate": float(self.in_purchase_rate.value()),
        }
        try:
            r = api_client.patch_json(f"{API_LOANS}/{self.loan_id}", payload)
            data = r.json()
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "بروزرسانی وام ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "بروزرسانی وام ناموفق بود.")


class LoanViewDialog(QDialog):
    def __init__(self, loan_id: int, parent=None):
        super().__init__(parent)
        self.loan_id = loan_id
        self.setWindowTitle("مشاهده وام | View Loan")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._item = _load_loan(loan_id)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight); form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18); form.setVerticalSpacing(10)

        def add_row(label_fa: str, value: str, selectable: bool = True):
            # RTL label: add colon between label and value
            row = QWidget(); hl = QHBoxLayout(row); hl.setContentsMargins(0,0,0,0); hl.setSpacing(8)
            lbl = QLabel(label_fa + ":")
            lbl.setStyleSheet("font-weight:600; color:#212529;")
            val = QLabel(value or "-")
            if selectable:
                val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setWordWrap(True)
            # Force RTL alignment for both
            lbl.setLayoutDirection(Qt.RightToLeft)
            val.setLayoutDirection(Qt.RightToLeft)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            hl.addWidget(lbl, 0)
            hl.addWidget(val, 1)
            form.addRow(row)

        add_row("شناسه", str(self._item.get("id", "")))
        add_row("نام بانک", self._item.get("bank_name", ""))
        add_row("نوع وام", self._item.get("loan_type", ""))
        add_row("مدت", self._item.get("duration", ""))
        # Format amounts nicely
        try:
            amount_fmt = f"{float(self._item.get('amount') or 0):,.2f}"
        except Exception:
            amount_fmt = str(self._item.get('amount', ''))
        add_row("مبلغ", amount_fmt)
        add_row("نام مالک", self._item.get("owner_full_name", ""))
        add_row("تلفن", self._item.get("owner_phone", ""))
        add_row("تاریخ بازدید", str(self._item.get("visit_date") or ""))
        add_row("وضعیت وام", self._item.get("loan_status", ""))
        add_row("معرف", self._item.get("introducer", ""))
        add_row("نوع پرداخت", self._item.get("payment_type", ""))
        try:
            pr_fmt = f"{float(self._item.get('purchase_rate') or 0):,.2f}"
        except Exception:
            pr_fmt = str(self._item.get('purchase_rate', ''))
        add_row("نرخ خرید", pr_fmt)

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


def delete_loan_with_confirm(parent, loan_id: int) -> bool:
    m = QMessageBox.question(parent, "حذف وام", "آیا از حذف این وام اطمینان دارید؟")
    if m == QMessageBox.StandardButton.Yes:
        try:
            r = api_client.delete(f"{API_LOANS}/{loan_id}")
            data = r.json()
            if data.get("status") == "success":
                return True
            QMessageBox.warning(parent, "خطا", data.get("message", "حذف ناموفق بود."))
        except Exception:
            QMessageBox.critical(parent, "خطا", "حذف ناموفق بود.")
    return False