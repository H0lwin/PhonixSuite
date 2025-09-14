# -*- coding: utf-8 -*-
"""Financial module with reports and transaction management"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox, QTextEdit, QComboBox,
    QMessageBox, QGridLayout, QFrame, QScrollArea, QSizePolicy, QDialog,
    QProgressBar, QSplitter, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QPalette, QPixmap, QPainter, QPen, QBrush, QColor


class SimpleBarChart(QWidget):
    """Simple bar chart widget for displaying financial trend data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(260)
        self.setStyleSheet("background-color: white; border: none; border-radius: 8px;")
    
    def set_data(self, trend_data):
        """Set chart data - list of dicts with 'month', 'revenue', 'expenses', 'profit'"""
        self.data = trend_data[-6:] if len(trend_data) > 6 else trend_data  # Last 6 months
        self.update()
    
    def paintEvent(self, event):
        if not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Chart area and axes
        rect = self.rect().adjusted(48, 28, -24, -56)
        axis_pen = QPen(QColor(222, 226, 230))
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
        
        # Find max value for scaling
        max_val = 0
        for item in self.data:
            max_val = max(max_val, item.get('revenue', 0), item.get('expenses', 0))
        max_val = max(max_val, 1)
        
        # Grid lines (4)
        painter.setPen(QPen(QColor(241, 243, 245)))
        for i in range(1, 5):
            y = rect.top() + i * rect.height() / 5
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        
        # Grouped bars
        group_width = rect.width() // len(self.data)
        bar_width = max(10, int(group_width * 0.28))
        for i, item in enumerate(self.data):
            revenue = item.get('revenue', 0)
            expenses = item.get('expenses', 0)
            group_left = rect.left() + i * group_width + int((group_width - (bar_width*2 + 8)) / 2)
            
            rev_height = int((revenue / max_val) * rect.height())
            rev_rect = QRect(group_left, rect.bottom() - rev_height, bar_width, rev_height)
            painter.fillRect(rev_rect, QColor(25, 135, 84))
            
            exp_height = int((expenses / max_val) * rect.height())
            exp_rect = QRect(group_left + bar_width + 8, rect.bottom() - exp_height, bar_width, exp_height)
            painter.fillRect(exp_rect, QColor(220, 53, 69))
            
            # Month label (full Persian label expected from backend)
            painter.setPen(QColor(73, 80, 87))
            painter.drawText(group_left - 10, rect.bottom() + 18, bar_width*2 + 28, 18, Qt.AlignCenter, item.get('month', ''))
        
        # Legend
        legend_y = rect.top() - 6
        painter.fillRect(rect.left() + 8, legend_y, 14, 14, QColor(25, 135, 84))
        painter.setPen(QColor(73, 80, 87))
        painter.drawText(rect.left() + 26, legend_y + 12, "درآمد")
        painter.fillRect(rect.left() + 72, legend_y, 14, 14, QColor(220, 53, 69))
        painter.drawText(rect.left() + 90, legend_y + 12, "هزینه")


class FinancialMetricsCard(QFrame):
    """Enhanced card widget for displaying financial metrics with animations"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", icon: str = "", color: str = "#0d6efd", parent=None):
        super().__init__(parent)
        self.color = color
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: none;
                border-radius: 12px;
                background: white;
                margin: 8px;
            }}
            QFrame:hover {{
                border: none;
            }}
        """)
        # Increase card height for better readability
        self.setFixedHeight(168)
        
        # Apply drop shadow effect programmatically (Qt way)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter if not icon else Qt.AlignLeft)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Value label (no border box)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "color: #222; font-size: 22px; font-weight: 800; padding: 4px;"
        )
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Subtitle with trend indicator
        self.subtitle_label = QLabel(subtitle) if subtitle else QLabel()
        self.subtitle_label.setStyleSheet("color: #666; font-size: 11px; font-weight: 500; background: transparent; border: none; padding: 0;")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)
        
        # Progress indicator (optional)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                text-align: center;
                height: 6px;
                background-color: #f1f3f5;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress_bar)
    
    def update_value(self, value: str, subtitle: str = "", progress: int = -1):
        self.value_label.setText(value)
        if subtitle:
            # Add trend arrows for better visualization
            if "+" in subtitle:
                trend_icon = "↗️"  # Up arrow
                color = "#198754"  # Green
            elif "-" in subtitle and subtitle.startswith("(-"):
                trend_icon = "↘️"  # Down arrow  
                color = "#dc3545"  # Red
            else:
                trend_icon = "➡️"  # Right arrow
                color = "#6c757d"  # Gray
            
            self.subtitle_label.setText(f"{trend_icon} {subtitle}")
            self.subtitle_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 500; background: transparent; border: none;")
        
        if progress >= 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setVisible(False)


class FinancialReportsTab(QWidget):
    """Tab 1: Financial Reports with key metrics and trend analysis"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_financial_metrics()
        
        # Auto-refresh every 30 seconds
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_financial_metrics)
        self.refresh_timer.start(30000)  # 30 seconds
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("گزارش‌های مالی")
        header.setStyleSheet("font-size: 24px; font-weight: 800; color: #222; margin-bottom: 4px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        subtitle = QLabel("مرور شاخص‌ها و روند مالی شش ماهه")
        subtitle.setStyleSheet("color:#6c757d; font-size:13px; margin-bottom: 8px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # Metrics Cards
        metrics_group = QGroupBox("")
        metrics_group.setStyleSheet("QGroupBox { border: none; margin-top:0; }")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setHorizontalSpacing(12)
        metrics_layout.setVerticalSpacing(12)
        
        # Create enhanced metric cards with icons and colors
        self.creditors_card = FinancialMetricsCard(
            "مجموع بدهکاران", 
            "در حال بارگذاری...",
            icon="💰",
            color="#dc3545"  # Red for debts
        )
        self.revenue_card = FinancialMetricsCard(
            "درآمد ماهیانه", 
            "در حال بارگذاری...",
            icon="📈",
            color="#198754"  # Green for revenue
        )
        self.profit_card = FinancialMetricsCard(
            "سود خالص", 
            "در حال بارگذاری...",
            icon="📊",
            color="#0d6efd"  # Blue for profit
        )
        
        metrics_layout.addWidget(self.creditors_card, 0, 0)
        metrics_layout.addWidget(self.revenue_card, 0, 1)
        metrics_layout.addWidget(self.profit_card, 0, 2)
        
        layout.addWidget(metrics_group)
        
        # Trend Analysis Section - Split into Chart and Table
        trend_group = QGroupBox("تحلیل روند مالی (۶ ماه گذشتا)")
        trend_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 16px; 
                border: 2px solid #0d6efd;
                border-radius: 8px;
                margin: 10px 0;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 8px;
                color: #0d6efd;
            }
        """)
        trend_layout = QVBoxLayout(trend_group)
        
        # Make chart full-width at top, table below
        chart_title = QLabel("نمودار روند")
        chart_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #0d6efd; margin-bottom: 6px;")
        chart_title.setAlignment(Qt.AlignRight)
        trend_layout.addWidget(chart_title)
        
        self.trend_chart = SimpleBarChart()
        self.trend_chart.setMinimumHeight(260)
        self.trend_chart.setStyleSheet("background:white; border: none; border-radius: 8px;")
        trend_layout.addWidget(self.trend_chart)
        
        # Table section under chart
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_title = QLabel("جدول تفصیلی")
        table_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #0d6efd; margin: 10px 0 6px 0;")
        table_title.setAlignment(Qt.AlignRight)
        table_layout.addWidget(table_title)
        
        self.trend_table = QTableWidget(0, 4)
        self.trend_table.setHorizontalHeaderLabels(["ماه", "درآمد (تومان)", "هزینه (تومان)", "سود (تومان)"])
        self.trend_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trend_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trend_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trend_table.setAlternatingRowColors(True)
        self.trend_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
        self.trend_table.setShowGrid(False)
        self.trend_table.setMaximumHeight(360)
        
        table_layout.addWidget(self.trend_table)
        trend_layout.addWidget(table_container)
        layout.addWidget(trend_group)
        
        # Refresh button
        refresh_button = QPushButton("نوسازی داده‌ها")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        refresh_button.clicked.connect(self.load_financial_metrics)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)
        layout.addLayout(button_layout)
        
        layout.addStretch()
    
    def format_currency(self, amount: float) -> str:
        """Format amount as Persian currency with proper separators"""
        if amount == 0:
            return "۰ تومان"
        
        # Format with thousands separator
        formatted = "{:,.0f}".format(abs(amount))
        sign = "منفی " if amount < 0 else ""
        
        # Convert to Persian numbers
        persian_nums = {
            '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
            '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹',
            ',': '،'  # Persian comma
        }
        
        for eng, per in persian_nums.items():
            formatted = formatted.replace(eng, per)
            
        return f"{sign}{formatted} تومان"
    
    def format_percentage(self, percentage: float) -> str:
        """Format percentage with appropriate color"""
        if percentage > 0:
            return f"(+{percentage:.1f}% نسبت به ماه قبل)"
        elif percentage < 0:
            return f"({percentage:.1f}% نسبت به ماه قبل)"
        else:
            return "(بدون تغییر نسبت به ماه قبل)"
    
    def load_financial_metrics(self):
        """Load and display financial metrics"""
        try:
            # Ensure we have the latest session info
            from ..state import session as _session
            if not _session.get_token():
                self.show_error("خطا در احراز هویت. لطفاً مجدداً وارد شوید")
                return
                
            from ..services import api_client
            
            # Load metrics
            response = api_client.get("http://127.0.0.1:5000/api/finance/metrics")
            data = response.json()
            
            if data.get("status") == "success":
                metrics = data.get("metrics", {})
                
                # Update creditors card
                total_creditors = metrics.get("total_creditors", 0)
                if self.creditors_card.subtitle_label:
                    creditors_subtitle = f"مجموع بدهی‌های فعال"
                else:
                    creditors_subtitle = ""
                self.creditors_card.update_value(
                    self.format_currency(total_creditors),
                    creditors_subtitle
                )
                
                # Update revenue card  
                monthly_revenue = metrics.get("monthly_revenue", {})
                revenue_amount = monthly_revenue.get("amount", 0)
                revenue_change = monthly_revenue.get("percentage_change", 0)
                revenue_subtitle = self.format_percentage(revenue_change)
                self.revenue_card.update_value(
                    self.format_currency(revenue_amount),
                    revenue_subtitle
                )
                
                # Update profit card
                net_profit = metrics.get("net_profit", {})
                profit_amount = net_profit.get("amount", 0)
                profit_change = net_profit.get("percentage_change", 0)
                profit_subtitle = self.format_percentage(profit_change)
                # Color code the profit card based on positive/negative
                profit_color = "#198754" if profit_amount >= 0 else "#dc3545"
                self.profit_card.value_label.setStyleSheet(f"color: {profit_color}; font-size: 20px; font-weight: bold;")
                self.profit_card.update_value(
                    self.format_currency(profit_amount),
                    profit_subtitle
                )
                
            else:
                error_msg = data.get("message", "خطای نامشخص")
                if "401" in error_msg or "Unauthorized" in error_msg:
                    self.show_error("نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
                else:
                    self.show_error("خطا در بارگذاری شاخص‌های مالی: " + error_msg)
                
        except Exception as e:
            logging.exception("Error loading financial metrics")
            error_str = str(e)
            if "401" in error_str or "Unauthorized" in error_str:
                self.show_error("نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
            else:
                self.show_error("خطا در اتصال به سرور")
        
        # Load trend data
        self.load_trend_data()
    
    def load_trend_data(self):
        """Load and display 6-month trend data in both chart and table"""
        try:
            from ..services import api_client
            
            response = api_client.get("http://127.0.0.1:5000/api/finance/trend")
            data = response.json()
            
            if data.get("status") == "success":
                trend_data = data.get("trend", [])
                
                # Update chart with trend data
                if hasattr(self, 'trend_chart'):
                    self.trend_chart.set_data(trend_data)
                
                # Clear existing table data
                self.trend_table.setRowCount(0)
                
                # Populate table with enhanced formatting
                for item in trend_data:
                    row = self.trend_table.rowCount()
                    self.trend_table.insertRow(row)
                    
                    month = item.get("month", "")
                    revenue = item.get("revenue", 0)
                    expenses = item.get("expenses", 0)
                    profit = item.get("profit", 0)
                    
                    # Month with Persian formatting
                    month_item = QTableWidgetItem(self.format_persian_month(month))
                    month_item.setTextAlignment(Qt.AlignCenter)
                    self.trend_table.setItem(row, 0, month_item)
                    
                    # Revenue with green background for positive values
                    revenue_item = QTableWidgetItem(self.format_currency(revenue))
                    revenue_item.setTextAlignment(Qt.AlignCenter)
                    if revenue > 0:
                        revenue_item.setBackground(QColor(25, 135, 84, 30))  # Light green
                    self.trend_table.setItem(row, 1, revenue_item)
                    
                    # Expenses with light red background
                    expenses_item = QTableWidgetItem(self.format_currency(expenses))
                    expenses_item.setTextAlignment(Qt.AlignCenter)
                    if expenses > 0:
                        expenses_item.setBackground(QColor(220, 53, 69, 30))  # Light red
                    self.trend_table.setItem(row, 2, expenses_item)
                    
                    # Profit with color coding
                    profit_item = QTableWidgetItem(self.format_currency(profit))
                    profit_item.setTextAlignment(Qt.AlignCenter)
                    if profit > 0:
                        profit_item.setBackground(QColor(25, 135, 84))  # Green
                        profit_item.setForeground(Qt.white)
                    elif profit < 0:
                        profit_item.setBackground(QColor(220, 53, 69))  # Red
                        profit_item.setForeground(Qt.white)
                    else:
                        profit_item.setBackground(QColor(108, 117, 125))  # Gray
                        profit_item.setForeground(Qt.white)
                    
                    self.trend_table.setItem(row, 3, profit_item)
                    
            else:
                error_msg = data.get("message", "خطای نامشخص")
                if "401" in error_msg or "Unauthorized" in error_msg:
                    self.show_error("نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
                else:
                    self.show_error("خطا در بارگذاری روند مالی: " + error_msg)
                
        except Exception as e:
            logging.exception("Error loading trend data")
            error_str = str(e)
            if "401" in error_str or "Unauthorized" in error_str:
                self.show_error("نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
            else:
                self.show_error("خطا در بارگذاری روند مالی")
    
    def format_persian_month(self, month_str: str) -> str:
        """Convert English month names to Persian"""
        persian_months = {
            'January': 'ژانویه',
            'February': 'فوریه', 
            'March': 'مارس',
            'April': 'آوریل',
            'May': 'مه',
            'June': 'ژوئن',
            'July': 'ژوئیه',
            'August': 'آگوست',
            'September': 'سپتامبر',
            'October': 'اکتبر',
            'November': 'نوامبر',
            'December': 'دسامبر'
        }
        
        for eng, per in persian_months.items():
            if eng in month_str:
                return month_str.replace(eng, per)
        return month_str
    
    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.warning(self, "خطا", message)


class TransactionDialog(QDialog):
    """Dialog for adding income/expense transactions"""
    
    def __init__(self, transaction_type: str, parent=None):
        super().__init__(parent)
        self.transaction_type = transaction_type
        self.setWindowTitle(f"افزودن {transaction_type}")
        self.setModal(True)
        self.resize(720, 260)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Amount input
        self.amount_input = QSpinBox()
        self.amount_input.setRange(1, 999999999)
        self.amount_input.setSuffix(" تومان")
        self.amount_input.setSingleStep(10000)
        try:
            # Show thousand separators if available in this Qt version
            self.amount_input.setGroupSeparatorShown(True)
        except Exception:
            pass
        form_layout.addRow("مبلغ:", self.amount_input)
        
        # Description input
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText(f"توضیحات {self.transaction_type}")
        form_layout.addRow("توضیحات:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("ثبت")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #157347;
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("لغو")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5c636a;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def get_values(self):
        """Get entered values"""
        amount = float(self.amount_input.value())
        description = self.description_input.text().strip()
        return amount, description


class FinancialManagementTab(QWidget):
    """Tab 2: Financial Management for manual transactions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        # Ensure we have a currency formatter for this tab
        if not hasattr(self, 'format_currency'):
            def _fmt(amount: float) -> str:
                formatted = "{:,.0f}".format(abs(amount))
                persian_nums = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹', ',':'،'}
                for e,p in persian_nums.items():
                    formatted = formatted.replace(e, p)
                sign = "منفی " if amount < 0 else ""
                return f"{sign}{formatted} تومان"
            self.format_currency = _fmt  # type: ignore
        self.load_transactions()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("مدیریت مالی")
        header.setStyleSheet("font-size: 24px; font-weight: 800; color: #222; margin-bottom: 4px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        subtitle = QLabel("ثبت درآمد و هزینه‌های دستی")
        subtitle.setStyleSheet("color:#6c757d; font-size:13px; margin-bottom: 8px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        add_income_btn = QPushButton("افزودن درآمد")
        add_income_btn.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #157347;
            }
        """)
        add_income_btn.clicked.connect(self.add_income)
        
        add_expense_btn = QPushButton("افزودن هزینه")
        add_expense_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bb2d3b;
            }
        """)
        add_expense_btn.clicked.connect(self.add_expense)
        
        refresh_btn = QPushButton("نوسازی")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5c636a;
            }
        """)
        refresh_btn.clicked.connect(self.load_transactions)
        
        button_layout.addWidget(add_income_btn)
        button_layout.addWidget(add_expense_btn)
        button_layout.addStretch()
        button_layout.addWidget(refresh_btn)
        layout.addLayout(button_layout)
        
        # Transactions table
        table_group = QGroupBox("فهرست تراکنش‌ها")
        table_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; }")
        table_layout = QVBoxLayout(table_group)
        
        self.transactions_table = QTableWidget(0, 5)
        self.transactions_table.setHorizontalHeaderLabels(["نوع", "مبلغ (تومان)", "توضیحات", "تاریخ", "حذف"])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transactions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transactions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
        self.transactions_table.setShowGrid(False)
        # Increase row height for better readability (~2x)
        vh = self.transactions_table.verticalHeader()
        vh.setDefaultSectionSize(56)
        vh.setMinimumSectionSize(56)
        
        table_layout.addWidget(self.transactions_table)
        layout.addWidget(table_group)
        
        layout.addStretch()
    
    def add_income(self):
        """Show dialog to add income"""
        dialog = TransactionDialog("درآمد", self)
        if dialog.exec():
            amount, description = dialog.get_values()
            if description:  # Check if description is provided
                self.save_transaction("revenue", amount, description)
            else:
                QMessageBox.warning(self, "خطا", "لطفاً توضیحات تراکنش را وارد کنید")
    
    def add_expense(self):
        """Show dialog to add expense"""
        dialog = TransactionDialog("هزینه", self)
        if dialog.exec():
            amount, description = dialog.get_values()
            if description:  # Check if description is provided
                self.save_transaction("expense", amount, description)
            else:
                QMessageBox.warning(self, "خطا", "لطفاً توضیحات تراکنش را وارد کنید")
    
    def save_transaction(self, transaction_type: str, amount: float, description: str):
        """Save transaction to server"""
        try:
            from ..services import api_client
            
            endpoint = f"http://127.0.0.1:5000/api/finance/{transaction_type}"
            payload = {
                "source": description,
                "amount": amount
            }
            
            response = api_client.post_json(endpoint, payload)
            data = response.json()
            
            if data.get("status") == "success":
                QMessageBox.information(self, "موفقیت", "تراکنش با موفقیت ثبت شد")
                self.load_transactions()
            else:
                QMessageBox.warning(self, "خطا", data.get("message", "خطا در ثبت تراکنش"))
                
        except Exception as e:
            logging.exception("Error saving transaction")
            QMessageBox.warning(self, "خطا", "خطا در اتصال به سرور")
    
    def load_transactions(self):
        """Load and display transactions with enhanced formatting"""
        try:
            # Check authentication
            from ..state import session as _session
            if not _session.get_token():
                QMessageBox.warning(self, "خطا", "نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
                return
                
            from ..services import api_client
            
            response = api_client.get("http://127.0.0.1:5000/api/finance/transactions")
            data = response.json()
            
            if data.get("status") == "success":
                transactions = data.get("transactions", [])
                
                # Clear existing data
                self.transactions_table.setRowCount(0)
                
                # Populate table with enhanced formatting
                for transaction in transactions:
                    row = self.transactions_table.rowCount()
                    self.transactions_table.insertRow(row)
                    # Ensure taller row (~2x)
                    try:
                        self.transactions_table.setRowHeight(row, 56)
                    except Exception:
                        pass
                    
                    # Type with icon and color
                    trans_type = transaction.get("type", "")
                    if trans_type == "revenue":
                        type_text = "💰 درآمد"
                        bg_color = QColor(25, 135, 84)
                    else:
                        type_text = "📉 هزینه"
                        bg_color = QColor(220, 53, 69)
                        
                    type_item = QTableWidgetItem(type_text)
                    type_item.setBackground(bg_color)
                    type_item.setForeground(Qt.white)
                    type_item.setTextAlignment(Qt.AlignCenter)
                    self.transactions_table.setItem(row, 0, type_item)
                    
                    # Amount with Persian formatting
                    amount = transaction.get("amount", 0)
                    amount_item = QTableWidgetItem(self.format_currency(amount))
                    amount_item.setTextAlignment(Qt.AlignCenter)
                    amount_item.setTextAlignment(Qt.AlignCenter)
                    # Light background color based on type
                    if trans_type == "revenue":
                        amount_item.setBackground(QColor(25, 135, 84, 30))
                    else:
                        amount_item.setBackground(QColor(220, 53, 69, 30))
                    self.transactions_table.setItem(row, 1, amount_item)
                    
                    # Description
                    description = transaction.get("description", "")
                    desc_item = QTableWidgetItem(description)
                    desc_item.setTextAlignment(Qt.AlignCenter)
                    self.transactions_table.setItem(row, 2, desc_item)
                    
                    # Date with Persian formatting
                    date = transaction.get("date", "")
                    if date:
                        # Convert to more readable format
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                            formatted_date = dt.strftime("%Y/%m/%d - %H:%M")
                        except:
                            formatted_date = date
                    else:
                        formatted_date = "نامعلوم"
                    
                    date_item = QTableWidgetItem(formatted_date)
                    date_item.setTextAlignment(Qt.AlignCenter)
                    self.transactions_table.setItem(row, 3, date_item)
                    
                    # Enhanced delete button per row (no transform)
                    delete_btn = QPushButton("🗑️ حذف")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            padding: 6px 12px;
                            border-radius: 4px;
                            font-weight: bold;
                            border: none;
                        }
                        QPushButton:hover {
                            background-color: #bb2d3b;
                        }
                        QPushButton:pressed {
                            background-color: #a02834;
                        }
                    """)
                    
                    # Store transaction info in button
                    trans_id = transaction.get("id")
                    trans_type = transaction.get("type")
                    delete_btn.clicked.connect(lambda checked, tid=trans_id, ttype=trans_type: self.delete_transaction(tid, ttype))
                    
                    self.transactions_table.setCellWidget(row, 4, delete_btn)
                    
            else:
                error_msg = data.get("message", "خطای نامشخص")
                if "401" in error_msg or "Unauthorized" in error_msg:
                    QMessageBox.warning(self, "خطا", "نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
                else:
                    QMessageBox.warning(self, "خطا", "خطا در بارگذاری تراکنش‌ها: " + error_msg)
                
        except Exception as e:
            logging.exception("Error loading transactions")
            error_str = str(e)
            if "401" in error_str or "Unauthorized" in error_str:
                QMessageBox.warning(self, "خطا", "نشست شما منقضی شده. لطفاً مجدداً وارد شوید")
            else:
                QMessageBox.warning(self, "خطا", "خطا در بارگذاری تراکنش‌ها")
    
    def delete_transaction(self, transaction_id: int, transaction_type: str):
        """Delete a transaction"""
        reply = QMessageBox.question(
            self, "تأیید حذف",
            "آیا از حذف این تراکنش اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from ..services import api_client
                
                url = f"http://127.0.0.1:5000/api/finance/transactions/{transaction_id}?type={transaction_type}"
                response = api_client.delete(url)
                data = response.json()
                
                if data.get("status") == "success":
                    QMessageBox.information(self, "موفقیت", "تراکنش حذف شد")
                    self.load_transactions()
                else:
                    QMessageBox.warning(self, "خطا", data.get("message", "خطا در حذف تراکنش"))
                    
            except Exception as e:
                logging.exception("Error deleting transaction")
                QMessageBox.warning(self, "خطا", "خطا در اتصال به سرور")


class FinanceView(QWidget):
    """Main Finance module with tabbed interface"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #f1f3f5;
                padding: 10px 18px;
                margin-right: 6px;
                border-radius: 8px;
                border: none;
                color: #333;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #0d6efd;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # Add tabs
        reports_tab = FinancialReportsTab()
        management_tab = FinancialManagementTab()
        
        tab_widget.addTab(reports_tab, "گزارش‌های مالی")
        tab_widget.addTab(management_tab, "مدیریت مالی")
        
        layout.addWidget(tab_widget)
