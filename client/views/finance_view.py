# -*- coding: utf-8 -*-
"""Enhanced Financial Module with Professional Charts and Tables"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox, QTextEdit, QComboBox,
    QMessageBox, QGridLayout, QFrame, QScrollArea, QSizePolicy, QDialog,
    QDialogButtonBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush, QColor

from client.components.financial_chart import FinancialChart
from client.components.advanced_table import AdvancedTable
from client.components.jalali_date import (
    format_persian_currency, format_persian_number, 
    get_jalali_month_year, JalaliDateEdit, to_jalali_dt_str
)
from client.services import api_client
from client.state import session as client_session


class MetricCard(QWidget):
    """Enhanced metric card with animations and better styling"""
    
    def __init__(self, title: str, icon: str, color: str = "#0d6efd", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon = icon
        self.color = color
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedHeight(120)
        self.setStyleSheet(f"""
            QWidget {{
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                border-left: 4px solid {self.color};
            }}
            QWidget:hover {{
                border-color: {self.color};
                background: #f8f9fa;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet(f"font-size: 24px; color: {self.color};")
        icon_label.setFixedSize(32, 32)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #6c757d;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)
        layout.addLayout(header_layout)
        
        # Value
        self.value_label = QLabel("در حال بارگذاری...")
        self.value_label.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: bold; 
            color: {self.color};
            margin: 4px 0;
        """)
        layout.addWidget(self.value_label)
        
        # Subtitle
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 11px; color: #6c757d;")
        layout.addWidget(self.subtitle_label)
    
    def update_value(self, value: str, subtitle: str = ""):
        """Update card value and subtitle"""
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)


class TransactionDialog(QDialog):
    """Dialog for adding financial transactions"""
    
    def __init__(self, transaction_type: str, parent=None):
        super().__init__(parent)
        self.transaction_type = transaction_type  # "revenue" or "expense"
        self.setWindowTitle(f"افزودن {'درآمد' if transaction_type == 'revenue' else 'هزینه'}")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Form
        form_group = QGroupBox(f"اطلاعات {'درآمد' if self.transaction_type == 'revenue' else 'هزینه'}")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        
        # Source
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText(f"منبع {'درآمد' if self.transaction_type == 'revenue' else 'هزینه'}")
        form_layout.addRow("منبع:", self.source_input)
        
        # Amount
        self.amount_input = QSpinBox()
        self.amount_input.setRange(0, 999999999)
        self.amount_input.setSuffix(" تومان")
        form_layout.addRow("مبلغ:", self.amount_input)
        
        # Date
        self.date_input = JalaliDateEdit()
        form_layout.addRow("تاریخ:", self.date_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("توضیحات اختیاری...")
        form_layout.addRow("توضیحات:", self.description_input)
        
        layout.addWidget(form_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 8px;
            }
            QLineEdit, QSpinBox, QTextEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
                border-color: #0d6efd;
            }
        """)
    
    def get_data(self) -> Dict[str, Any]:
        """Get form data"""
        return {
            "source": self.source_input.text().strip(),
            "amount": self.amount_input.value(),
            "date": self.date_input.get_gregorian_iso(),
            "description": self.description_input.toPlainText().strip()
        }


class FinanceView(QWidget):
    """Enhanced Financial Management View"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        title = QLabel("💰 مدیریت مالی")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 نوسازی")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5c636a;
            }
        """)
        refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                color: #495057;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #0d6efd;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
            }
        """)
        
        # Financial Reports Tab
        self._setup_reports_tab()
        
        # Financial Management Tab
        self._setup_management_tab()
        
        layout.addWidget(self.tabs)

        # If user role lacks finance access, disable finance interactions
        role = (client_session.get_role() or "").lower()
        if role not in ("admin", "accountant", "secretary"):
            self.setEnabled(True)  # keep visible
            # Disable management tab entirely
            try:
                idx = self.tabs.indexOf(self.tabs.findChild(QWidget, None))
            except Exception:
                idx = -1
            # Hide action buttons in management tab if exist
            try:
                for btn in self.findChildren(QPushButton):
                    if any(x in btn.text() for x in ("افزودن درآمد", "افزودن هزینه")):
                        btn.setEnabled(False)
            except Exception:
                pass
    
    def _setup_reports_tab(self):
        """Setup financial reports tab with vertical scrolling and roomier sections"""
        # Container for scrollable content
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(32)
        container_layout.setContentsMargins(28, 28, 28, 28)
        
        # Metrics cards
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("background: #f8f9fa; border-radius: 10px; padding: 24px;")
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setHorizontalSpacing(24)
        metrics_layout.setVerticalSpacing(20)
        
        # Create metric cards
        self.revenue_card = MetricCard("درآمد ماهانه", "📈", "#28a745")
        self.expense_card = MetricCard("هزینه ماهانه", "📉", "#dc3545")
        self.profit_card = MetricCard("سود ماهانه", "💰", "#17a2b8")
        self.creditors_card = MetricCard("بستانکاران فعال", "👥", "#fd7e14")
        
        metrics_layout.addWidget(self.revenue_card, 0, 0)
        metrics_layout.addWidget(self.expense_card, 0, 1)
        metrics_layout.addWidget(self.profit_card, 0, 2)
        metrics_layout.addWidget(self.creditors_card, 0, 3)
        
        container_layout.addWidget(metrics_frame)
        
        # Chart and table splitter (taller sections)
        splitter = QSplitter(Qt.Vertical)
        
        # Financial chart
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background: white; border: 1px solid #e9ecef; border-radius: 8px;")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        
        self.financial_chart = FinancialChart()
        self.financial_chart.setMinimumHeight(560)
        chart_layout.addWidget(self.financial_chart)
        
        splitter.addWidget(chart_frame)
        
        # Trend table
        table_frame = QFrame()
        table_frame.setStyleSheet("background: white; border: 1px solid #e9ecef; border-radius: 8px;")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)
        
        table_title = QLabel("📊 جدول روند مالی")
        table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        table_layout.addWidget(table_title)
        
        self.trend_table = AdvancedTable(["ماه", "درآمد", "هزینه", "سود"])
        self.trend_table.setMinimumHeight(520)
        table_layout.addWidget(self.trend_table)
        
        splitter.addWidget(table_frame)
        splitter.setSizes([640, 520])
        
        container_layout.addWidget(splitter, 1)
        
        # Scroll area wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        
        self.tabs.addTab(scroll, "📊 گزارش‌های مالی")
    
    def _setup_management_tab(self):
        """Setup financial management tab with vertical scrolling"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(28)
        container_layout.setContentsMargins(24, 24, 24, 24)
        
        # Action buttons
        actions_frame = QFrame()
        actions_frame.setStyleSheet("background: #f8f9fa; border-radius: 10px; padding: 20px;")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setSpacing(12)
        
        # Add revenue button
        add_revenue_btn = QPushButton("➕ افزودن درآمد")
        add_revenue_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        add_revenue_btn.clicked.connect(lambda: self._add_transaction("revenue"))
        
        # Add expense button
        add_expense_btn = QPushButton("➖ افزودن هزینه")
        add_expense_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        add_expense_btn.clicked.connect(lambda: self._add_transaction("expense"))
        
        actions_layout.addWidget(add_revenue_btn)
        actions_layout.addWidget(add_expense_btn)
        actions_layout.addStretch()
        
        container_layout.addWidget(actions_frame)
        
        # Transactions table
        transactions_frame = QFrame()
        transactions_frame.setStyleSheet("background: white; border: 1px solid #e9ecef; border-radius: 10px;")
        transactions_layout = QVBoxLayout(transactions_frame)
        transactions_layout.setContentsMargins(20, 20, 20, 20)
        
        transactions_title = QLabel("💳 تراکنش‌های مالی")
        transactions_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        transactions_layout.addWidget(transactions_title)
        
        self.transactions_table = AdvancedTable([
            "نوع", "منبع", "مبلغ", "تاریخ", "توضیحات", "شناسه"
        ])
        self.transactions_table.add_action_column(["حذف"])
        self.transactions_table.action_clicked.connect(self._on_transaction_action)
        self.transactions_table.setMinimumHeight(420)
        
        transactions_layout.addWidget(self.transactions_table)
        
        container_layout.addWidget(transactions_frame)
        
        # Scroll wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        
        self.tabs.addTab(scroll, "⚙️ مدیریت مالی")
    
    def _load_data(self):
        """Load all financial data"""
        try:
            # Check access
            if not client_session.get_token():
                self._show_error("خطا در احراز هویت")
                return
            
            # Load metrics
            self._load_metrics()
            
            # Load trend data
            self._load_trend_data()
            
            # Load transactions
            self._load_transactions()
            
        except Exception as e:
            logging.error(f"Error loading financial data: {e}")
            self._show_error("خطا در بارگذاری اطلاعات مالی")
    
    def _load_metrics(self):
        """Load financial metrics"""
        try:
            # Guard: only roles with finance access should call this endpoint
            from client.state import session as client_session
            role = (client_session.get_role() or "").lower()
            if role not in ("admin", "accountant", "secretary"):
                # Show safe empty state without calling the API
                self.revenue_card.update_value(format_persian_currency(0), "محدود")
                self.expense_card.update_value(format_persian_currency(0), "محدود")
                self.profit_card.update_value(format_persian_currency(0), "محدود")
                self.creditors_card.update_value(format_persian_currency(0), "محدود")
                return

            response = api_client.get("/api/finance/metrics")
            
            if response.status_code == 403:
                # Silent handling: keep UI clean
                self.revenue_card.update_value(format_persian_currency(0), "محدود")
                self.expense_card.update_value(format_persian_currency(0), "محدود")
                self.profit_card.update_value(format_persian_currency(0), "محدود")
                self.creditors_card.update_value(format_persian_currency(0), "محدود")
                return
            
            data = response.json()
            
            if data.get("status") == "success":
                metrics = data.get("metrics", {})
                
                # Update cards
                monthly_revenue = metrics.get("monthly_revenue", {})
                revenue_amount = monthly_revenue.get("amount", 0)
                revenue_change = monthly_revenue.get("percentage_change", 0)
                self.revenue_card.update_value(
                    format_persian_currency(revenue_amount),
                    f"تغییر: {revenue_change:+.1f}%" if revenue_change != 0 else "بدون تغییر"
                )
                
                monthly_expenses = metrics.get("monthly_expenses", {})
                expense_amount = monthly_expenses.get("amount", 0)
                expense_change = monthly_expenses.get("percentage_change", 0)
                self.expense_card.update_value(
                    format_persian_currency(expense_amount),
                    f"تغییر: {expense_change:+.1f}%" if expense_change != 0 else "بدون تغییر"
                )
                
                profit = revenue_amount - expense_amount
                self.profit_card.update_value(
                    format_persian_currency(profit),
                    "سود خالص ماهانه"
                )
                
                total_creditors = metrics.get("total_creditors", 0)
                self.creditors_card.update_value(
                    format_persian_currency(total_creditors),
                    "مجموع بدهی‌های فعال"
                )
                
        except Exception as e:
            logging.error(f"Error loading metrics: {e}")
    
    def _load_trend_data(self):
        """Load trend data for chart and table"""
        try:
            # Guard: restrict finance endpoints by role
            from client.state import session as client_session
            role = (client_session.get_role() or "").lower()
            if role not in ("admin", "accountant", "secretary"):
                # Clear chart and table to safe empty state
                self.financial_chart.set_data([])
                self.trend_table.set_data([])
                return

            response = api_client.get("/api/finance/trend")
            
            if response.status_code == 403:
                # Silent: show empty
                self.financial_chart.set_data([])
                self.trend_table.set_data([])
                return
            
            data = api_client.parse_json(response)
            
            # Defensive: data must be a dict with status
            if not isinstance(data, dict):
                logging.error(f"Trend API returned non-dict: type={type(data)}")
                self.financial_chart.set_data([])
                self.trend_table.set_data([])
                return
            
            if data.get("status") != "success":
                # Gracefully show empty state on error
                msg = data.get("message")
                if msg:
                    logging.error(f"Trend API error: {msg}")
                self.financial_chart.set_data([])
                self.trend_table.set_data([])
                return
            
            # Extract and validate trend list
            trend_raw = data.get("trend", [])
            if callable(trend_raw) or not isinstance(trend_raw, list):
                # Guard against accidentally passing a method/object
                logging.error(f"Invalid trend payload type: {type(trend_raw)}")
                trend_raw = []
            
            # Keep only dict items
            trend_data = [it for it in trend_raw if isinstance(it, dict)]
            
            # Update chart with raw numeric data
            self.financial_chart.set_data(trend_data)
            
            # Build formatted table rows
            table_data = []
            for item in trend_data:
                try:
                    table_data.append({
                        "ماه": get_jalali_month_year(item.get("month", "")),
                        "درآمد": format_persian_currency(item.get("revenue", 0) or 0),
                        "هزینه": format_persian_currency(item.get("expenses", 0) or 0),
                        "سود": format_persian_currency(item.get("profit", 0) or 0)
                    })
                except Exception:
                    # Skip any malformed item
                    continue
            
            self.trend_table.set_data(table_data)
            
        except Exception:
            logging.exception("Error loading trend data")
    
    def _load_transactions(self):
        """Load financial transactions"""
        try:
            response = api_client.get("/api/finance/transactions")
            
            if response.status_code == 403:
                return
            
            data = api_client.parse_json(response)
            
            if data.get("status") == "success":
                transactions = data.get("transactions", [])
                
                # Format for table (fields per backend: id,type,description,amount,date)
                table_data = []
                for trans in transactions:
                    desc = trans.get("description", "") or ""
                    table_data.append({
                        "نوع": "💰 درآمد" if trans.get("type") == "revenue" else "💸 هزینه",
                        "منبع": desc,
                        "مبلغ": format_persian_currency(trans.get("amount", 0)),
                        "تاریخ": to_jalali_dt_str(trans.get("date", "")),
                        "توضیحات": desc[:50] + "..." if len(desc) > 50 else desc,
                        "شناسه": str(trans.get("id"))
                    })
                
                self.transactions_table.set_data(table_data)
                
        except Exception as e:
            logging.error(f"Error loading transactions: {e}")
    
    def _add_transaction(self, transaction_type: str):
        """Add new financial transaction"""
        dialog = TransactionDialog(transaction_type, self)
        
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            
            if not data["source"] or data["amount"] <= 0:
                QMessageBox.warning(self, "خطا", "لطفاً تمام فیلدهای ضروری را پر کنید")
                return
            
            try:
                endpoint = f"/api/finance/{transaction_type}"
                response = api_client.post_json(endpoint, data)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "موفقیت", f"{'درآمد' if transaction_type == 'revenue' else 'هزینه'} با موفقیت ثبت شد")
                    self._load_data()  # Refresh data
                else:
                    QMessageBox.warning(self, "خطا", "خطا در ثبت تراکنش")
                    
            except Exception as e:
                logging.error(f"Error adding transaction: {e}")
                QMessageBox.critical(self, "خطا", "خطا در ارتباط با سرور")
    
    def _on_transaction_action(self, action: str, row_index: int):
        """Handle transaction table actions"""
        if action == "حذف":
            reply = QMessageBox.question(
                self, "تأیید حذف", 
                "آیا از حذف این تراکنش اطمینان دارید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Calculate selected transaction from table
                current_page = getattr(self.transactions_table, 'current_page', 0)
                rows_per_page = getattr(self.transactions_table, 'rows_per_page', 20)
                start_idx = current_page * rows_per_page
                data_index = start_idx + row_index
                try:
                    row = self.transactions_table.filtered_data[data_index]
                except Exception:
                    row = None
                if not row:
                    return
                txn_id = (row.get("شناسه") or "").strip()
                txn_type = "revenue" if "درآمد" in (row.get("نوع") or "") else "expense"
                if not txn_id:
                    QMessageBox.warning(self, "خطا", "شناسه تراکنش یافت نشد")
                    return
                try:
                    resp = api_client.delete(f"/api/finance/transactions/{txn_id}?type={txn_type}")
                    if resp.status_code == 200:
                        QMessageBox.information(self, "موفقیت", "تراکنش حذف شد")
                        # فقط لیست تراکنش‌ها را تازه‌سازی کن تا روی نمودار/جداول روند اثر نگذارد
                        self._load_transactions()
                    elif resp.status_code == 404:
                        QMessageBox.warning(self, "خطا", "تراکنش پیدا نشد")
                    else:
                        QMessageBox.warning(self, "خطا", "حذف تراکنش ناموفق بود")
                except Exception:
                    QMessageBox.critical(self, "خطا", "ارتباط با سرور ناموفق بود")
    
    def _show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "خطا", message)
    
    def _show_access_denied(self):
        """Show access denied message"""
        QMessageBox.warning(self, "عدم دسترسی", "شما دسترسی به اطلاعات مالی ندارید")