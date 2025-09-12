# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QMessageBox, QRadioButton, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QDateEdit, QAbstractSpinBox, QProgressBar
)
from PySide6.QtCore import Qt, QDate, QLocale

from ..services import api_client
from ..utils.styles import style_dialog_buttons

API_CREDITORS = "http://127.0.0.1:5000/api/creditors"


def _load_creditor(cred_id: int) -> Dict[str, Any]:
    """Load a creditor safely, raising RuntimeError with a friendly message on failure."""
    try:
        r = api_client.get(f"{API_CREDITORS}/{cred_id}")
        data = api_client.parse_json(r)
    except Exception:
        data = {"status": "error", "message": "Network error"}
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "Failed to load creditor"))
    return data.get("item", {})


class CreditorAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن بستانکار")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_full_name = QLineEdit(); self.in_full_name.setPlaceholderText("نام و نام خانوادگی")
        self.in_amount = QDoubleSpinBox(); self.in_amount.setRange(0, 10_000_000_000); self.in_amount.setDecimals(2)
        self.in_amount.setLocale(QLocale(QLocale.English))
        self.in_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_amount.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        self.in_desc = QTextEdit(); self.in_desc.setPlaceholderText("توضیحات")

        form.addRow("نام", self.in_full_name)
        form.addRow("مبلغ", self.in_amount)
        form.addRow("توضیحات", self.in_desc)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "full_name": self.in_full_name.text().strip(),
            "amount": float(self.in_amount.value()),
            "description": self.in_desc.toPlainText().strip(),
        }
        if not payload["full_name"]:
            QMessageBox.warning(self, "خطا", "نام بستانکار الزامی است.")
            return
        try:
            r = api_client.post_json(API_CREDITORS, payload)
            data = api_client.parse_json(r)
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "ثبت ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "ثبت ناموفق بود.")


class CreditorEditDialog(QDialog):
    def __init__(self, cred_id: int, parent=None):
        super().__init__(parent)
        self.cred_id = cred_id
        self.setWindowTitle("ویرایش بستانکار")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._item = _load_creditor(cred_id)

        layout = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignRight)

        self.in_full_name = QLineEdit(self._item.get("full_name", ""))
        self.in_amount = QDoubleSpinBox(); self.in_amount.setRange(0, 10_000_000_000); self.in_amount.setDecimals(2)
        self.in_amount.setLocale(QLocale(QLocale.English))
        self.in_amount.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.in_amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.in_amount.setStyleSheet("QDoubleSpinBox{padding:6px 8px;}")
        try:
            self.in_amount.setValue(float(self._item.get("amount") or 0))
        except Exception:
            self.in_amount.setValue(0)
        self.in_desc = QTextEdit(self._item.get("description", ""))

        form.addRow("نام", self.in_full_name)
        form.addRow("مبلغ", self.in_amount)
        form.addRow("توضیحات", self.in_desc)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self):
        payload = {
            "full_name": self.in_full_name.text().strip(),
            "amount": float(self.in_amount.value()),
            "description": self.in_desc.toPlainText().strip(),
        }
        try:
            r = api_client.patch_json(f"{API_CREDITORS}/{self.cred_id}", payload)
            data = api_client.parse_json(r)
            if data.get("status") == "success":
                self.accept()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "بروزرسانی ناموفق بود."))
        except Exception:
            QMessageBox.critical(self, "خطا", "بروزرسانی ناموفق بود.")


class CreditorViewDialog(QDialog):
    def __init__(self, cred_id: int, parent=None):
        super().__init__(parent)
        self.cred_id = cred_id
        self.setWindowTitle("مشاهده بستانکار | View Creditor")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._item = _load_creditor(cred_id)

        layout = QVBoxLayout(self)

        # Row 1: Creditor name and status
        row1 = QLabel(f"{self._item.get('full_name','')}  |  وضعیت: {self._item.get('settlement_status','')}")
        row1.setStyleSheet("font-weight:600;")
        row1.setWordWrap(True)
        layout.addWidget(row1)
        # Row 1b: Creditor Info - Loan metadata
        loan_id = self._item.get('loan_id')
        loan_rate = self._item.get('loan_rate')
        bank_name = self._item.get('bank_name')
        owner_phone = self._item.get('owner_phone')
        meta_parts = []
        if loan_id is not None: meta_parts.append(f"Loan ID: {loan_id}")
        if loan_rate is not None: 
            try:
                meta_parts.append(f"Rate: {float(loan_rate or 0):,.2f}")
            except Exception:
                meta_parts.append(f"Rate: {loan_rate}")
        if bank_name: meta_parts.append(f"Bank: {bank_name}")
        if owner_phone: meta_parts.append(f"Phone: {owner_phone}")
        if meta_parts:
            meta_lbl = QLabel(" | ".join(meta_parts))
            meta_lbl.setStyleSheet("color:#495057;")
            meta_lbl.setWordWrap(True)
            layout.addWidget(meta_lbl)

        # Row 2: Progress
        total = float(self._item.get("amount") or 0)
        paid = float(self._item.get("paid_amount") or 0)
        try:
            pct = 0 if total <= 0 else int(round((paid/total)*100))
        except Exception:
            pct = 0
        prog_lbl = QLabel(f"پرداخت شده: {paid:,.2f} از {total:,.2f} ({pct}%)")
        prog_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(prog_lbl)
        bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(pct); bar.setTextVisible(True)
        layout.addWidget(bar)

        # Row 3: Installments table
        ins = self._item.get("installments", [])
        if ins:
            tbl = QTableWidget(0, 3)
            tbl.setHorizontalHeaderLabels(["تاریخ", "مبلغ", "توضیحات"]) 
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
            for it in ins:
                r = tbl.rowCount(); tbl.insertRow(r)
                tbl.setItem(r, 0, QTableWidgetItem(str(it.get("date") or "")))
                try:
                    amt = float(it.get("amount") or 0); amt_txt = f"{amt:,.2f}"
                except Exception:
                    amt_txt = str(it.get("amount", ""))
                amt_item = QTableWidgetItem(amt_txt); amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(r, 1, amt_item)
                tbl.setItem(r, 2, QTableWidgetItem(it.get("notes") or ""))
            layout.addWidget(tbl)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        style_dialog_buttons(buttons)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PayDialog(QDialog):
    """Payment dialog supporting Installments or Full Payment."""
    def __init__(self, cred_id: int, cred_name: str, total_amount: float, parent=None):
        super().__init__(parent)
        self.cred_id = cred_id
        self.cred_name = cred_name
        self.total_amount = float(total_amount or 0)
        self.setWindowTitle(f"پرداخت به {cred_name}")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        # Load existing creditor with installments for summary and history
        try:
            item = _load_creditor(self.cred_id)
        except Exception:
            item = {"amount": self.total_amount, "paid_amount": 0.0, "remaining_amount": self.total_amount, "installments": []}
        total = float(item.get("amount") or self.total_amount)
        paid = float(item.get("paid_amount") or 0)
        remaining = max(total - paid, 0)
        summary = QLabel(f"کل بدهی: {total:,.2f} | پرداخت‌شده: {paid:,.2f} | باقیمانده: {remaining:,.2f}")
        summary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(summary)
        # Existing installments table (with edit/delete)
        self.tbl_existing = QTableWidget(0, 5)
        self.tbl_existing.setHorizontalHeaderLabels(["تاریخ", "مبلغ", "توضیحات", "✏️", "🗑️"]) 
        self.tbl_existing.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_existing.setAlternatingRowColors(True)
        layout.addWidget(self.tbl_existing)
        self._reload_existing_installments()

        # Mode selection
        mode_row = QHBoxLayout()
        self.rb_installments = QRadioButton("اقساط")
        self.rb_full = QRadioButton("تسویه کامل")
        self.rb_installments.setChecked(True)
        mode_row.addWidget(self.rb_installments); mode_row.addWidget(self.rb_full); mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # Installments table (repeater)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["مبلغ", "تاریخ", "توضیحات", ""]) 
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        add_row_btn = QPushButton("افزودن قسط")
        add_row_btn.setStyleSheet("QPushButton{background:#198754;color:white;padding:6px 12px;border-radius:6px;} QPushButton:hover{background:#157347;}") 
        add_row_btn.clicked.connect(self._add_row)

        # Container for installment UI
        self.installments_container = QWidget(); inst_l = QVBoxLayout(self.installments_container); inst_l.setContentsMargins(0,0,0,0); inst_l.setSpacing(6)
        inst_l.addWidget(self.tbl)
        # Sum row
        sum_row = QHBoxLayout(); sum_row.setSpacing(6)
        self.lbl_sum = QLabel("جمع اقساط: 0.00")
        sum_row.addStretch(1); sum_row.addWidget(self.lbl_sum); 
        inst_l.addLayout(sum_row)
        inst_l.addWidget(add_row_btn)
        layout.addWidget(self.installments_container)

        # Full payment fields (container)
        self.full_container = QWidget(); full_row = QHBoxLayout(self.full_container); full_row.setContentsMargins(0,0,0,0)
        self.full_date = QDateEdit(QDate.currentDate()); self.full_date.setDisplayFormat("yyyy-MM-dd")
        self.full_notes = QLineEdit(); self.full_notes.setPlaceholderText("یادداشت تسویه")
        full_row.addWidget(QLabel("تاریخ تسویه")); full_row.addWidget(self.full_date)
        full_row.addWidget(QLabel("یادداشت")); full_row.addWidget(self.full_notes)
        layout.addWidget(self.full_container)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_mode_ui()
        self.rb_installments.toggled.connect(self._update_mode_ui)
        self.rb_full.toggled.connect(self._update_mode_ui)

        # Store summary label for refresh recalculation
        self._summary_label = summary

    def _update_mode_ui(self):
        inst_mode = self.rb_installments.isChecked()
        # Toggle visibility of containers
        self.installments_container.setVisible(inst_mode)
        self.full_container.setVisible(not inst_mode)
        # First time ensure at least one row in installment mode
        if inst_mode and self.tbl.rowCount() == 0:
            self._add_row()
        # Update sum on mode change
        self._recalc_sum()

    def _add_row(self):
        r = self.tbl.rowCount(); self.tbl.insertRow(r)
        # Amount
        amt = QLineEdit(); amt.setPlaceholderText("0.00")
        amt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amt.textChanged.connect(lambda _: self._recalc_sum())
        self.tbl.setCellWidget(r, 0, amt)
        # Date
        dt = QDateEdit(QDate.currentDate()); dt.setDisplayFormat("yyyy-MM-dd")
        self.tbl.setCellWidget(r, 1, dt)
        # Notes
        notes = QLineEdit(); notes.setPlaceholderText("توضیحات")
        self.tbl.setCellWidget(r, 2, notes)
        # Delete button
        btn_del = QPushButton("🗑")
        btn_del.setToolTip("حذف قسط")
        btn_del.setFixedWidth(32)
        btn_del.clicked.connect(lambda _, row=r: self._delete_row(row))
        self.tbl.setCellWidget(r, 3, btn_del)
        # Ensure sum updates
        self._recalc_sum()

    def _submit(self):
        try:
            if self.rb_installments.isChecked():
                # Gather installments
                n = self.tbl.rowCount()
                payloads: List[Dict[str, Any]] = []
                for i in range(n):
                    amt_w = self.tbl.cellWidget(i, 0)
                    dt_w = self.tbl.cellWidget(i, 1)
                    notes_w = self.tbl.cellWidget(i, 2)
                    try:
                        amt = float((amt_w.text() or "0").replace(",", ""))
                    except Exception:
                        amt = 0.0
                    date_str = dt_w.date().toString("yyyy-MM-dd")
                    notes = notes_w.text().strip()
                    if amt <= 0:
                        continue
                    payloads.append({"amount": amt, "date": date_str, "notes": notes})
                if not payloads:
                    QMessageBox.information(self, "توجه", "هیچ قسط معتبری وارد نشده است.")
                    return
                # Post each installment and ensure success
                for p in payloads:
                    resp = api_client.post_json(f"{API_CREDITORS}/{self.cred_id}/installments", p)
                    data = api_client.parse_json(resp)
                    if data.get("status") != "success":
                        raise RuntimeError(data.get("message", "ثبت قسط ناموفق بود."))
                # Close dialog on success
                self.accept()
            else:
                # Full payment
                date_str = self.full_date.date().toString("yyyy-MM-dd")
                notes = (self.full_notes.text() or "").strip()
                resp = api_client.post_json(f"{API_CREDITORS}/{self.cred_id}/settle", {"date": date_str, "notes": notes})
                data = api_client.parse_json(resp)
                if data.get("status") != "success":
                    raise RuntimeError(data.get("message", "تسویه ناموفق بود."))
                # After settlement, close so parent view can refresh and move item to History
                self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "خطا", str(exc) or "ثبت پرداخت ناموفق بود.")

    def _delete_row(self, row: int):
        # Remove the row and reindex delete callbacks
        if 0 <= row < self.tbl.rowCount():
            self.tbl.removeRow(row)
            # Rebind delete buttons to correct rows
            for i in range(self.tbl.rowCount()):
                w = self.tbl.cellWidget(i, 3)
                if isinstance(w, QPushButton):
                    w.clicked.disconnect()
                    w.clicked.connect(lambda _, rr=i: self._delete_row(rr))
        self._recalc_sum()

    def _recalc_sum(self):
        total = 0.0
        for i in range(self.tbl.rowCount()):
            amt_w = self.tbl.cellWidget(i, 0)
            try:
                total += float((amt_w.text() or "0").replace(",", ""))
            except Exception:
                pass
        self.lbl_sum.setText(f"جمع اقساط: {total:,.2f}")

    def _reload_existing_installments(self):
        # Reload installments and totals from server and redraw existing table + summary line
        try:
            r = api_client.get(f"{API_CREDITORS}/{self.cred_id}/installments")
            data = api_client.parse_json(r)
            if data.get("status") != "success":
                return
            ins = data.get("installments", [])
            paid = float(data.get("paid_amount") or 0)
            # We need total debt for remaining calc; fetch base creditor info
            base = _load_creditor(self.cred_id)
            total = float(base.get("amount") or 0)
            remaining = max(total - paid, 0)
            # Update summary label
            self._summary_label.setText(f"کل بدهی: {total:,.2f} | پرداخت‌شده: {paid:,.2f} | باقیمانده: {remaining:,.2f}")
            # Redraw existing installments table
            self.tbl_existing.setRowCount(0)
            for it in ins:
                r = self.tbl_existing.rowCount(); self.tbl_existing.insertRow(r)
                # Date
                dt = QDateEdit(); dt.setDisplayFormat("yyyy-MM-dd")
                try:
                    qd = QDate.fromString(str(it.get("date") or ""), "yyyy-MM-dd")
                    if qd and qd.isValid():
                        dt.setDate(qd)
                except Exception:
                    pass
                self.tbl_existing.setCellWidget(r, 0, dt)
                # Amount (editable)
                amt = QLineEdit()
                try:
                    amt.setText(f"{float(it.get('amount') or 0):,.2f}")
                except Exception:
                    amt.setText(str(it.get('amount') or ""))
                amt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_existing.setCellWidget(r, 1, amt)
                # Notes
                notes = QLineEdit(); notes.setText(it.get("notes") or "")
                self.tbl_existing.setCellWidget(r, 2, notes)
                # Edit button
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(28, 28)
                btn_edit.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
                inst_id = it.get("id")
                btn_edit.clicked.connect(lambda _, row=r, iid=inst_id: self._save_existing_row(row, iid))
                self.tbl_existing.setCellWidget(r, 3, btn_edit)
                # Delete button
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(28, 28)
                btn_del.setStyleSheet("QPushButton{padding:0;border:1px solid #dee2e6;border-radius:6px;background:#ffffff;} QPushButton:hover{background:#f8f9fa}")
                btn_del.clicked.connect(lambda _, iid=inst_id: self._delete_existing(iid))
                self.tbl_existing.setCellWidget(r, 4, btn_del)
        except Exception:
            pass

    def _save_existing_row(self, row: int, inst_id: int):
        try:
            dt_w = self.tbl_existing.cellWidget(row, 0)
            amt_w = self.tbl_existing.cellWidget(row, 1)
            notes_w = self.tbl_existing.cellWidget(row, 2)
            # Parse amount
            try:
                amt = float((amt_w.text() or "0").replace(",", ""))
            except Exception:
                amt = 0.0
            payload = {
                "date": dt_w.date().toString("yyyy-MM-dd"),
                "amount": amt,
                "notes": (notes_w.text() or "").strip(),
            }
            api_client.patch_json(f"{API_CREDITORS}/{self.cred_id}/installments/{inst_id}", payload)
            self._reload_existing_installments()
        except Exception:
            QMessageBox.critical(self, "خطا", "بروزرسانی قسط ناموفق بود.")

    def _delete_existing(self, inst_id: int):
        try:
            api_client.delete(f"{API_CREDITORS}/{self.cred_id}/installments/{inst_id}")
            self._reload_existing_installments()
        except Exception:
            QMessageBox.critical(self, "خطا", "حذف قسط ناموفق بود.")