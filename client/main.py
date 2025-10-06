# -*- coding: utf-8 -*-
import sys
import json
import os
# Ensure 'client.*' imports work when running this file directly
import os as _os, sys as _sys
_parent = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
if _parent not in _sys.path:
    _sys.path.insert(0, _parent)
import logging
from logging.handlers import RotatingFileHandler
import requests
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QTextEdit,
    QDoubleSpinBox,
    QTabWidget,
    QGroupBox,
    QFormLayout,
    QBoxLayout,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QFontDatabase, QFont

# Global signals for inter-component communication
class GlobalSignals(QObject):
    employee_updated = Signal()
    
global_signals = GlobalSignals()

API_LOGIN = "/api/auth/login"
API_EMP_META = "/api/employees/meta"
API_EMP_CREATE = "/api/employees"


class پنجره_داشبورد(QWidget):
    def __init__(self, نمایش_نام: str, نقش: str, توکن: str, بازگشت_به_ورود):
        super().__init__()
        self.setWindowTitle("Phoenix")
        # Fullscreen layout per requirements
        self.showMaximized()
        self.بازگشت_به_ورود = بازگشت_به_ورود

        # Save session globally for API client
        try:
            from client.state import session as _session
        except Exception:
            from client.state import session as _session
        _session.set_session(توکن, نقش, نمایش_نام)

        # Auto check-in on login
        self._auto_check_in()

        # Start 60-min session timer; on timeout, force relogin
        self._session_timer = QTimer(self)
        self._session_timer.setInterval(60 * 60 * 1000)  # 60 minutes
        self._session_timer.setSingleShot(True)
        self._session_timer.timeout.connect(self._on_session_timeout)
        self._session_timer.start()

        # Heartbeat timer: keeps attendance session alive and crash-safe
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(30 * 1000)  # every 30s for higher reliability
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)
        self._heartbeat_timer.start()
        # Send an immediate heartbeat after login to create/refresh session promptly
        self._send_heartbeat()

        # Two-column layout: right sidebar (navigation), left content stack
        root = QHBoxLayout()

        # Sidebar (right) with navigation list
        sidebar = QVBoxLayout()
        header = QLabel(f"خوش آمدید، {نمایش_نام} ({'مدیر' if نقش == 'admin' else 'کاربر'})")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar.addWidget(header)

        # Using a tree for hierarchical admin tabs
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
        self.nav_tree = QTreeWidget(); self.nav_tree.setHeaderHidden(True); self.nav_tree.setStyleSheet("QTreeWidget{background:#ffffff;border:1px solid #ddd;} QTreeWidget::item{padding:6px 8px;} QTreeWidget::item:selected{background:#e6f2ff;}")
        sidebar.addWidget(self.nav_tree)

        btn_logout = QPushButton("خروج از حساب")
        btn_logout.clicked.connect(self._logout)
        sidebar.addWidget(btn_logout)

        # Content area (left) — stacked pages corresponding to sidebar items
        self.content_stack = QStackedWidget()

        # Helper to add placeholder pages
        def add_placeholder(title: str) -> int:
            w = QWidget(); v = QVBoxLayout(); lbl = QLabel(f"{title}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(lbl); w.setLayout(v)
            self.content_stack.addWidget(w); return self.content_stack.indexOf(w)

        # Build sidebar items based on role
        from PySide6.QtWidgets import QTreeWidgetItem
        self._page_index_map = {}
        if نقش == "admin":
            # Admin tree structure - Full access to everything
            root_admin = QTreeWidgetItem(["مدیریت (ادمین)"])
            self.nav_tree.addTopLevelItem(root_admin)
            # Overview real page
            overview_item = QTreeWidgetItem(["نمای کلی"]) ; root_admin.addChild(overview_item)
            from client.views.dashboard_overview import DashboardOverview as _DashboardOverview
            overview_page = _DashboardOverview()
            # Share session timer with dashboard for countdown
            if hasattr(self, "_session_timer"):
                try:
                    overview_page.set_session_timer(self._session_timer)
                except Exception:
                    pass
            self._page_index_map["نمای کلی"] = self.content_stack.addWidget(overview_page)
            # Loans (dropdown) — parent has no content, sub-tabs have content
            loans_root = QTreeWidgetItem(["وام‌ها"]) ; root_admin.addChild(loans_root)
            admin_loan_subtabs = ["همه وام‌ها", "خریداران وام"]
            for t in admin_loan_subtabs:
                child = QTreeWidgetItem([t]); loans_root.addChild(child)
                if t == "همه وام‌ها":
                    # Real page for All Loans
                    from client.views.loans_view import LoansView as _LoansView
                    page = _LoansView()
                    self._page_index_map[t] = self.content_stack.addWidget(page)
                elif t == "خریداران وام":
                    # Real page for Loan Buyers
                    from client.views.buyers_view import BuyersView as _BuyersView
                    page = _BuyersView()
                    self._page_index_map[t] = self.content_stack.addWidget(page)
                else:
                    self._page_index_map[t] = add_placeholder(t)
            # Other admin tabs
            emp_mgmt_item = QTreeWidgetItem(["مدیریت کارمندان"]); root_admin.addChild(emp_mgmt_item)
            self._page_index_map["مدیریت کارمندان"] = self.content_stack.addWidget(self._build_admin_users_tab())
            # Branch Management real page
            branches_item = QTreeWidgetItem(["مدیریت شعب"]) ; root_admin.addChild(branches_item)
            from client.views.branches_view import BranchesView as _BranchesView
            branches_page = _BranchesView()
            self._page_index_map["مدیریت شعب"] = self.content_stack.addWidget(branches_page)
            # Finance real page
            finance_item = QTreeWidgetItem(["مالی"]); root_admin.addChild(finance_item)
            from client.views.finance_view import FinanceView as _FinanceView
            finance_page = _FinanceView()
            self._page_index_map["مالی"] = self.content_stack.addWidget(finance_page)
            
            # Attendance real page
            att_item = QTreeWidgetItem(["حضور و غیاب"]); root_admin.addChild(att_item)
            from client.views.attendance_view import AttendanceView as _AttendanceView
            att_page = _AttendanceView()
            self._page_index_map["حضور و غیاب"] = self.content_stack.addWidget(att_page)
            # Activity report real page
            act_item = QTreeWidgetItem(["گزارش فعالیت"]); root_admin.addChild(act_item)
            from client.views.activity_view import ActivityView as _ActivityView
            act_page = _ActivityView()
            self._page_index_map["گزارش فعالیت"] = self.content_stack.addWidget(act_page)
            # تنظیمات حذف شد - نیازی نیست
            # Creditors real page
            creditors_item = QTreeWidgetItem(["بستانکاران"]); root_admin.addChild(creditors_item)
            from client.views.creditors_view import CreditorsView as _CreditorsView
            creditors_page = _CreditorsView()
            self._page_index_map["بستانکاران"] = self.content_stack.addWidget(creditors_page)
            # Expand admin tree; loans parent toggles expand/collapse only
            self.nav_tree.expandItem(root_admin)
        else:
            # Employee (non-admin) dashboard - Limited access
            root_emp = QTreeWidgetItem(["داشبورد کارمند"])
            self.nav_tree.addTopLevelItem(root_emp)
            
            # Overview for employees (limited info)
            overview_item = QTreeWidgetItem(["نمای کلی"]); root_emp.addChild(overview_item)
            from client.views.employee_overview import EmployeeOverview as _EmployeeOverview
            overview_page = _EmployeeOverview()
            self._page_index_map["نمای کلی"] = self.content_stack.addWidget(overview_page)
            
            # Limited loans view (only available loans with limited fields)
            loans_item = QTreeWidgetItem(["وام‌ها"]); root_emp.addChild(loans_item)
            from client.views.loans_view import LoansView as _LoansView
            loans_page = _LoansView(employee_mode=True)  # Pass employee mode flag
            self._page_index_map["وام‌ها"] = self.content_stack.addWidget(loans_page)
            
            # Employee's own buyers
            buyers_item = QTreeWidgetItem(["خریداران من"]); root_emp.addChild(buyers_item)
            from client.views.buyers_view import BuyersView as _BuyersView
            buyers_page = _BuyersView(employee_mode=True)  # Pass employee mode flag
            self._page_index_map["خریداران من"] = self.content_stack.addWidget(buyers_page)
            
            # Personal reports
            reports_item = QTreeWidgetItem(["گزارشات"]); root_emp.addChild(reports_item)
            reports_page = self._build_employee_reports()
            self._page_index_map["گزارشات"] = self.content_stack.addWidget(reports_page)
            
            self.nav_tree.expandItem(root_emp)

        # Navigation behavior: clicking items selects associated page if mapped
        def on_tree_item_clicked(item, _col):
            title = item.text(0).strip()
            # For admin: Clicking Loans root toggles expand/collapse; ignore content change
            # For employee: Allow clicking on loans since there's no expansion
            if title == "وام‌ها" and نقش == "admin":
                return
            idx = (self._page_index_map or {}).get(title)
            if idx is not None:
                # Ensure page refresh on each navigation
                self.content_stack.setCurrentIndex(idx)
                try:
                    w = self.content_stack.widget(idx)
                    # Prefer a generic refresh method if present
                    if hasattr(w, "_refresh") and callable(getattr(w, "_refresh")):
                        w._refresh()
                    elif hasattr(w, "_load_data") and callable(getattr(w, "_load_data")):
                        w._load_data()
                except Exception:
                    pass
        self.nav_tree.itemClicked.connect(on_tree_item_clicked)

        # Default page selection
        if نقش == "admin":
            self.content_stack.setCurrentIndex(self._page_index_map.get("نمای کلی", 0))
        else:
            self.content_stack.setCurrentIndex(self._page_index_map.get("نمای کلی", 0))
        

        # Assemble layout (content left, sidebar right)
        root.addWidget(self.content_stack, 4)
        side_container = QWidget(); side_container.setLayout(sidebar)
        side_container.setFixedWidth(280)
        root.addWidget(side_container, 0)
        self.setLayout(root)

    def _logout(self, relogin_message: str | None = None):
        # Use centralized client (will inject token)
        from client.services import api_client
        
        # Stop heartbeat to avoid extra calls during logout
        try:
            if hasattr(self, "_heartbeat_timer"):
                self._heartbeat_timer.stop()
        except Exception:
            pass
        
        # Final heartbeat to capture last activity if possible
        try:
            api_client.post_json("/api/attendance/heartbeat", {}, timeout=2)
        except Exception:
            pass

        # Auto check-out on logout with shorter timeout to prevent hanging
        try:
            api_client.post_json("/api/attendance/check-out", {}, timeout=2)
        except Exception:
            pass  # Ignore errors during logout
        
        try:
            api_client.post_json("/api/auth/logout", {}, timeout=2)
        except Exception:
            pass  # Ignore errors during logout
        
        # Clear session first to prevent further API calls
        from client.state import session as _session
        _session.clear_session()
        
        # Close dashboard and return to login
        try:
            self.close()
        except Exception:
            pass
        
        # Call the callback to return to login
        try:
            if callable(self.بازگشت_به_ورود):
                self.بازگشت_به_ورود()
        except Exception:
            pass
        
        # Show relogin message if provided
        if relogin_message:
            try:
                from PySide6.QtWidgets import QMessageBox
                # Use self as parent instead of None to avoid type error
                QMessageBox.information(self, "ورود مجدد", relogin_message)
            except Exception:
                pass

    def _on_session_timeout(self):
        # Force relogin after 60 minutes
        self._logout("برای ادامه کار دوباره وارد شوید (Login again)")
    
    def _auto_check_in(self):
        """Automatically check-in user when they log in"""
        try:
            from client.services import api_client
            api_client.post_json("/api/attendance/check-in", {}, timeout=3)
        except Exception:
            # Ignore errors during auto check-in to not disrupt login flow
            pass

    def _send_heartbeat(self):
        """Ping server to keep today's session alive and update last activity time."""
        try:
            from client.services import api_client
            api_client.post_json("/api/attendance/heartbeat", {}, timeout=2)
        except Exception:
            # do not spam logs; heartbeat is best-effort
            pass

    def closeEvent(self, event):
        """Ensure we attempt to persist last activity on window close (power loss safe best-effort)."""
        try:
            # Stop timers to avoid re-entrancy
            if hasattr(self, "_heartbeat_timer"):
                self._heartbeat_timer.stop()
        except Exception:
            pass
        try:
            from client.services import api_client
            # Try a quick heartbeat then checkout
            try:
                api_client.post_json("/api/attendance/heartbeat", {}, timeout=1)
            except Exception:
                pass
            try:
                api_client.post_json("/api/attendance/check-out", {}, timeout=1)
            except Exception:
                pass
        except Exception:
            pass
        try:
            super().closeEvent(event)
        except Exception:
            pass
    
    def _build_employee_overview(self, display_name: str) -> QWidget:
        """Build simple overview for employee users"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Welcome header
        title = QLabel(f"خوش آمدید، {display_name}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:24px; font-weight:bold; margin:20px; color:#2c5aa0;")
        layout.addWidget(title)
        
        # Employee info cards
        info_layout = QHBoxLayout()
        
        # Summary card
        summary_card = QGroupBox("خلاصه اطلاعات")
        summary_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 10px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 10px;
                color: #2c5aa0;
            }
        """)
        
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.addWidget(QLabel("• شما می‌توانید وام‌های موجود را مشاهده کنید"))
        summary_layout.addWidget(QLabel("• امکان ثبت و مدیریت خریداران خود را دارید"))
        summary_layout.addWidget(QLabel("• گزارشات شخصی خود را ببینید"))
        summary_layout.addWidget(QLabel("• دسترسی به تاریخچه‌ها محدود است"))
        
        info_layout.addWidget(summary_card)
        
        # Access info card  
        access_card = QGroupBox("محدودیت‌های دسترسی")
        access_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #f39c12;
                border-radius: 10px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 10px;
                color: #f39c12;
            }
        """)
        
        access_layout = QVBoxLayout(access_card)
        access_layout.addWidget(QLabel("• وام‌های فروخته‌شده قابل مشاهده نیستند"))
        access_layout.addWidget(QLabel("• فقط اطلاعات محدود وام‌ها نمایش داده می‌شود"))
        access_layout.addWidget(QLabel("• تنها خریداران ثبت‌شده توسط خودتان قابل ویرایش هستند"))
        access_layout.addWidget(QLabel("• دسترسی به مدیریت کارمندان و مالی ندارید"))
        
        info_layout.addWidget(access_card)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        widget.setStyleSheet("QWidget { background: white; }")
        return widget
    
    def _build_employee_reports(self) -> QWidget:
        """Build enhanced reports page for employees with proper styling and organization"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("گزارشات شخصی")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #2c5aa0;
            margin-bottom: 10px;
        """)
        
        subtitle = QLabel("نمای کلی فعالیت‌ها و آمار شما")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #6c757d; margin-bottom: 20px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        # Main content in a scrollable area for better organization
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        
        # Personal statistics summary card
        summary_card = QGroupBox("📈 خلاصه آمار")
        summary_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #17a2b8;
                border-radius: 12px;
                margin-top: 20px;
                padding: 20px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 15px;
                color: #17a2b8;
                background-color: white;
                border-radius: 6px;
            }
        """)
        
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setSpacing(15)
        
        # Create a grid layout for better organization
        grid_layout = QHBoxLayout()
        
        # Left column
        left_col = QVBoxLayout()
        self.lbl_my_buyers = QLabel("👥 در حال بارگذاری...")
        self.lbl_my_buyers.setStyleSheet("""
            padding: 10px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
        """)
        
        self.lbl_my_purchased_loans = QLabel("💰 در حال بارگذاری...")
        self.lbl_my_purchased_loans.setStyleSheet("""
            padding: 10px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
        """)
        
        left_col.addWidget(self.lbl_my_buyers)
        left_col.addWidget(self.lbl_my_purchased_loans)
        
        # Right column
        right_col = QVBoxLayout()
        self.lbl_total_amount = QLabel("📉 در حال محاسبه...")
        self.lbl_total_amount.setStyleSheet("""
            padding: 10px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
        """)
        
        self.lbl_success_rate = QLabel("🎯 در حال محاسبه...")
        self.lbl_success_rate.setStyleSheet("""
            padding: 10px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
        """)
        
        right_col.addWidget(self.lbl_total_amount)
        right_col.addWidget(self.lbl_success_rate)
        
        grid_layout.addLayout(left_col)
        grid_layout.addLayout(right_col)
        summary_layout.addLayout(grid_layout)
        
        content_layout.addWidget(summary_card)
        
        # Detailed status breakdown card
        status_card = QGroupBox("📋 جزئیات وضعیت خریداران")
        status_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #28a745;
                border-radius: 12px;
                margin-top: 20px;
                padding: 20px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 15px;
                color: #28a745;
                background-color: white;
                border-radius: 6px;
            }
        """)
        
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(10)
        
        self.lbl_status_breakdown = QLabel("🔄 در حال بارگذاری جزئیات...")
        self.lbl_status_breakdown.setStyleSheet("""
            padding: 15px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
        """)
        self.lbl_status_breakdown.setWordWrap(True)
        
        status_layout.addWidget(self.lbl_status_breakdown)
        content_layout.addWidget(status_card)
        
        # Access limitation notice with better styling
        notice_card = QGroupBox("⚠️ ملاحظات مهم")
        notice_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #ffc107;
                border-radius: 12px;
                margin-top: 20px;
                padding: 20px;
                background-color: #fffbf0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 15px;
                color: #ffc107;
                background-color: white;
                border-radius: 6px;
            }
        """)
        
        notice_layout = QVBoxLayout(notice_card)
        notice_layout.setSpacing(8)
        
        notices = [
            "• تمام اطلاعات فقط قابل مشاهده است و قابل ویرایش نیست",
            "• تغییر وضعیت و ثبت تاریخ تنها توسط مدیر یا کارگذار مسئول امکان‌پذیر است",
            "• برای اعمال تغییرات به بخش‌های مربوطه مراجعه کنید"
        ]
        
        for notice in notices:
            label = QLabel(notice)
            label.setStyleSheet("""
                padding: 8px;
                background-color: white;
                border-left: 4px solid #ffc107;
                border-radius: 4px;
                font-size: 13px;
            """)
            label.setWordWrap(True)
            notice_layout.addWidget(label)
        
        content_layout.addWidget(notice_card)
        
        layout.addLayout(content_layout)
        
        # Load personal stats
        self._load_employee_detailed_stats()
        
        layout.addStretch()
        widget.setLayout(layout)
        widget.setStyleSheet("QWidget { background: #f5f6fa; }")
        return widget
    
    def _load_employee_detailed_stats(self):
        """Load detailed personal statistics for employee reports with enhanced calculations"""
        try:
            from client.services import api_client
            
            # Get own buyers count and status breakdown
            r = api_client.get("/api/loan-buyers")
            data = r.json()
            if data.get("status") == "success":
                buyers = data.get("items", [])
                total_buyers = len(buyers)
                
                # Calculate purchased loans count (those with status 'loan_paid')
                purchased_count = sum(1 for buyer in buyers if buyer.get("processing_status") == "loan_paid")
                
                # Calculate total amount of purchased loans
                total_amount = 0
                for buyer in buyers:
                    if buyer.get("processing_status") == "loan_paid":
                        try:
                            amount = float(buyer.get("requested_amount") or 0)
                            total_amount += amount
                        except (ValueError, TypeError):
                            continue
                
                # Calculate success rate
                success_rate = (purchased_count / total_buyers * 100) if total_buyers > 0 else 0
                
                # Update labels with proper formatting
                self.lbl_my_buyers.setText(f"👥 تعداد کل خریداران: {total_buyers} نفر")
                self.lbl_my_purchased_loans.setText(f"💰 وام‌های خریداری‌شده: {purchased_count} فقره")
                self.lbl_total_amount.setText(f"📉 مجموع مبلغ: {total_amount:,.0f} تومان")
                self.lbl_success_rate.setText(f"🎯 نرخ موفقیت: {success_rate:.1f}%")
                
                # Status breakdown with better formatting
                status_counts = {}
                for buyer in buyers:
                    status = buyer.get("processing_status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                if status_counts:
                    status_text = "📋 تفکیک وضعیت خریداران:\n\n"
                    status_mapping = {
                        "request_registered": ("📅 درخواست ثبت شد", "#17a2b8"),
                        "under_review": ("🔍 در حال بررسی", "#ffc107"),
                        "rights_transfer": ("🔄 انتقال حقوق", "#fd7e14"),
                        "bank_validation": ("🏦 اعتبارسنجی بانکی", "#6f42c1"),
                        "loan_paid": ("✅ وام پرداخت شد", "#28a745"),
                        "guarantor_issue": ("⚠️ ضامن ناقص", "#dc3545"),
                        "borrower_issue": ("⚠️ اطلاعات وام‌گیرنده ناقص", "#dc3545"),
                    }
                    
                    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                        status_fa, color = status_mapping.get(status, (status, "#6c757d"))
                        percentage = (count / total_buyers * 100) if total_buyers > 0 else 0
                        status_text += f"{status_fa}: {count} نفر ({percentage:.1f}%)\n"
                    
                    self.lbl_status_breakdown.setText(status_text.strip())
                else:
                    self.lbl_status_breakdown.setText("📄 هنوز خریداری ثبت نشده است.")
                    
            else:
                # Error handling with user-friendly messages
                self.lbl_my_buyers.setText("❌ خطا در بارگذاری تعداد خریداران")
                self.lbl_my_purchased_loans.setText("❌ خطا در بارگذاری وام‌ها")
                self.lbl_total_amount.setText("❌ خطا در محاسبه مبلغ")
                self.lbl_success_rate.setText("❌ خطا در محاسبه نرخ")
                self.lbl_status_breakdown.setText("❌ خطا در بارگذاری اطلاعات")
            
        except Exception as e:
            # Connection error handling
            error_msg = "🚫 خطا در اتصال به سرور"
            self.lbl_my_buyers.setText(error_msg)
            self.lbl_my_purchased_loans.setText(error_msg)
            self.lbl_total_amount.setText(error_msg)
            self.lbl_success_rate.setText(error_msg)
            self.lbl_status_breakdown.setText(f"{error_msg}\nلطفاً اتصال اینترنت خود را بررسی کنید.")

    def _build_admin_users_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Search + Filters bar (top)
        filters_bar = QHBoxLayout(); filters_bar.setSpacing(8)
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("جستجو نام/نام خانوادگی")
        self.filter_branch = QComboBox(); self.filter_branch.setMinimumWidth(160)
        # Default options
        self.filter_branch.addItem("همه شعب", -1)
        # Wire up live filtering
        self.search_input.textChanged.connect(self._apply_filters)
        self.filter_branch.currentIndexChanged.connect(self._apply_filters)
        filters_bar.addWidget(self.search_input)
        filters_bar.addWidget(self.filter_branch)
        layout.addLayout(filters_bar)

        # Users Table Card
        table_card = QGroupBox("فهرست کاربران")
        table_card.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #ddd; border-radius:6px; margin-top:10px;} QGroupBox::title{subcontrol-origin: margin; subcontrol-position: top right; padding: 0 8px;}")
        table_layout = QVBoxLayout(); table_layout.setSpacing(8)

        self.tbl_users = QTableWidget(0, 8)
        self.tbl_users.setHorizontalHeaderLabels(["ID", "نام", "کدملی", "نقش", "وضعیت", "مشاهده", "ویرایش", "حذف"]) 
        self.tbl_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_users.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_users.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_users.setAlternatingRowColors(True)
        # Increase row height for readability (~double)
        self.tbl_users.verticalHeader().setDefaultSectionSize(45)
        self.tbl_users.setStyleSheet("QTableWidget{background:white;} QHeaderView::section{background:#f8f9fa; padding:6px; border:1px solid #e9ecef;} QTableWidget::item{padding:10px;}")
        table_layout.addWidget(self.tbl_users)

        # Controls under table
        controls = QHBoxLayout()
        btn_add = QPushButton("افزودن کارمند")
        btn_add.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#0b5ed7}")
        btn_add.clicked.connect(self._open_add_employee)
        btn_refresh = QPushButton("نوسازی فهرست"); btn_refresh.clicked.connect(self._load_users)
        for b in (btn_refresh,):
            b.setStyleSheet("QPushButton{background:#6c757d;color:white;padding:6px 12px;border-radius:4px;} QPushButton:hover{background:#5c636a}")
        controls.addWidget(btn_add); controls.addStretch(1); controls.addWidget(btn_refresh)
        table_layout.addLayout(controls)

        table_card.setLayout(table_layout)
        layout.addWidget(table_card)

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        widget.setLayout(layout)
        # Light theme, white background
        widget.setStyleSheet("QWidget{background:white;color:black;}")
        # Load meta (departments/branches) first so filters populate, then users
        self._load_meta()
        self._load_users()
        return widget

    def _load_meta(self):
        # Use centralized client to include token
        try:
            from client.services import api_client
            r = api_client.get(API_EMP_META)
            data = r.json()
        except Exception:
            self.lbl_status.setText("بارگذاری اطلاعات دپارتمان/شعبه ناموفق بود.")
            return
        # Populate top filters
        self.filter_branch.clear()
        self.filter_branch.addItem("همه شعب", -1)
        for b in data.get("branches", []):
            self.filter_branch.addItem(b.get("name", ""), b.get("id"))

    def _load_users(self):
        try:
            from client.services import api_client
            r = api_client.get(API_EMP_CREATE)
            data = r.json()
        except Exception:
            self.lbl_status.setText("بارگذاری لیست کاربران ناموفق بود.")
            return
        if data.get("status") == "success":
            items = data.get("items", [])
            # Cache all items for client-side filtering
            self._all_users = items
            self._render_users(self._all_users)
            if not items:
                self.lbl_status.setText("کاربری وجود ندارد.")
            else:
                self.lbl_status.setText("")
        else:
            self.lbl_status.setText(data.get("message", "خطا در دریافت لیست کاربران."))

    def _open_add_employee(self):
        from client.components.dialogs import EmployeeAddDialog
        dlg = EmployeeAddDialog(self)
        if dlg.exec():
            self._load_users()

    def _apply_filters(self):
        """Apply search text + branch filters client-side."""
        txt = (self.search_input.text() or "").strip().lower()
        br_id = self.filter_branch.currentData()
        def match(item):
            # name filtering: accepts first/last name parts in full_name
            if txt:
                name = (item.get("full_name") or "").lower()
                if txt not in name:
                    return False
            if br_id not in (None, -1):
                if item.get("branch_id") != br_id:
                    return False
            return True
        src = getattr(self, "_all_users", [])
        filtered = [it for it in src if match(it)]
        self._render_users(filtered)

    def _render_users(self, items):
        """Render users to table, keep action buttons and styling."""
        self.tbl_users.setRowCount(0)
        for it in items:
            row = self.tbl_users.rowCount(); self.tbl_users.insertRow(row)
            emp_id = it.get("id", "")
            self.tbl_users.setItem(row, 0, QTableWidgetItem(str(emp_id)))
            self.tbl_users.setItem(row, 1, QTableWidgetItem(it.get("full_name", "")))
            self.tbl_users.setItem(row, 2, QTableWidgetItem(it.get("national_id", "")))
            self.tbl_users.setItem(row, 3, QTableWidgetItem(it.get("role", "")))
            self.tbl_users.setItem(row, 4, QTableWidgetItem(it.get("status", "")))
            btn_view = QPushButton("نمایش")
            btn_edit = QPushButton("ویرایش")
            btn_del = QPushButton("حذف")
            for b, c in ((btn_view, "#198754"), (btn_edit, "#0d6efd"), (btn_del, "#dc3545")):
                b.setStyleSheet(f"QPushButton{{background:{c};color:white;padding:4px 8px;border-radius:4px;}} QPushButton:hover{{opacity:0.9;}}")
            btn_view.clicked.connect(lambda _, i=emp_id: self._view_employee(i))
            btn_edit.clicked.connect(lambda _, i=emp_id: self._edit_employee(i))
            btn_del.clicked.connect(lambda _, i=emp_id: self._delete_employee(i))
            self.tbl_users.setCellWidget(row, 5, btn_view)
            self.tbl_users.setCellWidget(row, 6, btn_edit)
            self.tbl_users.setCellWidget(row, 7, btn_del)

    def _view_employee(self, emp_id: int):
        from client.components.dialogs import EmployeeViewDialog
        dlg = EmployeeViewDialog(int(emp_id), self)
        dlg.exec()

    def _edit_employee(self, emp_id: int):
        from client.components.dialogs import EmployeeEditDialog
        dlg = EmployeeEditDialog(int(emp_id), self)
        if dlg.exec():
            self._load_users()
            # Emit signal to refresh other views
            global_signals.employee_updated.emit()

    def _delete_employee(self, emp_id: int):
        from client.components.dialogs import delete_employee_with_confirm
        if delete_employee_with_confirm(self, int(emp_id)):
            self.lbl_status.setText("کاربر حذف شد.")
            self._load_users()

    def _submit_new_user(self):
        # Collect values
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
            from client.services import api_client
            r = api_client.post_json(API_EMP_CREATE, payload)
            data = r.json()
        except Exception:
            self.lbl_status.setText("ثبت کاربر ناموفق بود.")
            return

        if data.get("status") == "success":
            self.lbl_status.setText("کاربر با موفقیت افزوده شد.")
            # reset essential fields
            self.in_full_name.clear()
            self.in_national_id.clear()
            self.in_password.clear()
            self.in_role.clear()
            self.in_phone.clear()
            self.in_address.clear()
            self.in_salary.setValue(0)
            self.cb_status.setCurrentIndex(0)
        else:
            self.lbl_status.setText(data.get("message", "خطایی رخ داد."))


class پنجره_ورود(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phoenix - ورود")
        QApplication.instance().setLayoutDirection(Qt.RightToLeft)

        self.چیدمان = QVBoxLayout(); self.چیدمان.setSpacing(14)

        title = QLabel("به سیستم مدیریت خوش آمدید")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:bold; margin-bottom:6px;")

        self.کدملی = QLineEdit(); self.کدملی.setPlaceholderText("کد ملی ۱۰ رقمی")
        self.رمز_عبور = QLineEdit(); self.رمز_عبور.setPlaceholderText("رمز عبور"); self.رمز_عبور.setEchoMode(QLineEdit.Password)

        self.دکمه_ورود = QPushButton("ورود")
        self.دکمه_ورود.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:8px 14px;border-radius:6px;} QPushButton:hover{background:#0b5ed7}")

        self.برچسب_وضعیت = QLabel(""); self.برچسب_وضعیت.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.برچسب_وضعیت.setStyleSheet("color:#dc3545;")

        card = QGroupBox("")
        card.setStyleSheet("QGroupBox{border:1px solid #dee2e6; border-radius:10px; padding:16px; background:#ffffff;} ")
        form = QVBoxLayout(card); form.setSpacing(10)
        form.addWidget(title)
        form.addWidget(self.کدملی)
        form.addWidget(self.رمز_عبور)
        form.addWidget(self.دکمه_ورود)
        form.addWidget(self.برچسب_وضعیت)

        self.چیدمان.addStretch(1)
        self.چیدمان.addWidget(card)
        self.چیدمان.addStretch(1)
        self.setLayout(self.چیدمان)

        self.setMinimumWidth(420)
        self.setStyleSheet("QLineEdit{padding:8px 10px;}")

        self.دکمه_ورود.clicked.connect(self.ارسال_ورود)

    def ارسال_ورود(self):
        national_id = self.کدملی.text().strip()
        password = self.رمز_عبور.text().strip()
        if not national_id or not password:
            self.برچسب_وضعیت.setText("لطفاً کد ملی و رمز عبور را وارد کنید.")
            return

        try:
            # Use auth service
            try:
                from client.services.auth_service import login as auth_login
            except Exception:
                from client.services.auth_service import login as auth_login
            body = auth_login(national_id, password)
        except Exception:
            self.برچسب_وضعیت.setText("اتصال به سرور برقرار نشد.")
            logging.exception("Failed to reach server for login")
            return

        if body.get("status") == "success":
            role = body.get("role", "user")
            display_name = body.get("display_name", "کاربر")
            token = body.get("token")
            logging.info("Login success for national_id: %s | role=%s", national_id, role)
            # Auto check-in for attendance (session start)
            try:
                from client.services import api_client
            except Exception:
                from client.services import api_client
            try:
                api_client.post_json("/api/attendance/check-in", {})
            except Exception:
                pass
            # Show dashboard and pass a callback to return to login on logout
            def back_to_login():
                self.show()
                self.کدملی.clear(); self.رمز_عبور.clear(); self.برچسب_وضعیت.clear()
            self.پنجره_داشبورد = پنجره_داشبورد(display_name, role, token, back_to_login)
            self.پنجره_داشبورد.show()
            self.hide()
        else:
            msg = body.get("message", "کد ملی یا رمز عبور نادرست است.")
            self.برچسب_وضعیت.setText(msg)
            logging.warning("Login failed for national_id: %s | message=%s", national_id, msg)


def configure_logging():
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "client.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)


def _apply_global_font(app: QApplication):
    """Load and apply Vazir font globally.
    When bundled with PyInstaller, fall back to _MEIPASS data dir.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "fonts"))
    if not os.path.exists(base_dir):
        # Fallback for PyInstaller onefile/onedir
        base_dir = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), "client", "assets", "fonts")
    candidates = [
        os.path.join(base_dir, "Vazir.ttf"),
        os.path.join(base_dir, "Vazir-Medium.ttf"),
        os.path.join(base_dir, "Vazir-Bold.ttf"),
        os.path.join(base_dir, "Vazir-Light.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)
    # Set default family and sizes
    app.setFont(QFont("Vazir", 11))


def main():
    configure_logging()
    برنامه = QApplication(sys.argv)
    برنامه.setLayoutDirection(Qt.RightToLeft)
    _apply_global_font(برنامه)
    # Light theme application-wide
    برنامه.setStyleSheet("""
        QWidget{background:#ffffff;color:#212529;}
        QLabel{color:#212529;}
        QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox {background:#ffffff; border:1px solid #ced4da; border-radius:4px; padding:4px;}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {border-color:#86b7fe;}
        QPushButton{background:#0d6efd;color:white;border:none;padding:6px 12px;border-radius:4px;}
        QPushButton:hover{background:#0b5ed7}
        QGroupBox{border:1px solid #dee2e6; border-radius:6px; margin-top:12px;}
        QHeaderView::section{background:#f8f9fa;}
    """)
    پنجره = پنجره_ورود()
    پنجره.resize(420, 240)
    پنجره.show()
    sys.exit(برنامه.exec())


if __name__ == "__main__":
    main()
