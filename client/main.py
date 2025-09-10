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
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont

API_LOGIN = "http://127.0.0.1:5000/api/auth/login"
API_EMP_META = "http://127.0.0.1:5000/api/employees/meta"
API_EMP_CREATE = "http://127.0.0.1:5000/api/employees"


class پنجره_داشبورد(QWidget):
    def __init__(self, نمایش_نام: str, نقش: str, توکن: str, بازگشت_به_ورود):
        super().__init__()
        self.setWindowTitle("داشبورد")
        # Fullscreen layout per requirements
        self.showMaximized()
        self.بازگشت_به_ورود = بازگشت_به_ورود

        # Save session globally for API client
        try:
            from client.state import session as _session
        except Exception:
            from .state import session as _session
        _session.set_session(توکن, نقش, نمایش_نام)

        # Two-column layout: right sidebar (navigation), left content stack
        root = QHBoxLayout()

        # Sidebar (right) with navigation list
        sidebar = QVBoxLayout()
        header = QLabel(f"خوش آمدید، {نمایش_نام} ({'مدیر' if نقش == 'admin' else 'کاربر'})")
        header.setAlignment(Qt.AlignCenter)
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
            lbl.setAlignment(Qt.AlignCenter); v.addWidget(lbl); w.setLayout(v)
            self.content_stack.addWidget(w); return self.content_stack.indexOf(w)

        # Build sidebar items based on role
        from PySide6.QtWidgets import QTreeWidgetItem
        self._page_index_map = {}
        if نقش == "admin":
            # Admin tree structure
            root_admin = QTreeWidgetItem(["مدیریت (ادمین)"])
            self.nav_tree.addTopLevelItem(root_admin)
            # Overview (placeholder)
            overview_item = QTreeWidgetItem(["نمای کلی"]) ; root_admin.addChild(overview_item)
            self._page_index_map["نمای کلی"] = add_placeholder("نمای کلی")
            # Loans (dropdown) — parent has no content, sub-tabs have content
            loans_root = QTreeWidgetItem(["وام‌ها"]) ; root_admin.addChild(loans_root)
            admin_loan_subtabs = ["همه وام‌ها", "خریداران وام"]
            for t in admin_loan_subtabs:
                child = QTreeWidgetItem([t]); loans_root.addChild(child)
                self._page_index_map[t] = add_placeholder(t)
            # Other admin tabs
            emp_mgmt_item = QTreeWidgetItem(["مدیریت کارمندان"]); root_admin.addChild(emp_mgmt_item)
            self._page_index_map["مدیریت کارمندان"] = self.content_stack.addWidget(self._build_admin_users_tab())
            for title in ["بستانکاران", "مدیریت شعب", "مالی", "حضور و غیاب", "گزارش فعالیت", "تنظیمات"]:
                item = QTreeWidgetItem([title]); root_admin.addChild(item)
                self._page_index_map[title] = add_placeholder(title)
            # Expand admin tree; loans parent toggles expand/collapse only
            self.nav_tree.expandItem(root_admin)
        else:
            # Employee (non-admin) tabs
            root_emp = QTreeWidgetItem(["کاربر"])
            self.nav_tree.addTopLevelItem(root_emp)
            for title in ["نمای کلی", "وام‌های من", "خریداران من", "گزارش‌ها"]:
                idx = add_placeholder(title)
                child = QTreeWidgetItem([title]); root_emp.addChild(child)
                self._page_index_map[title] = idx
            self.nav_tree.expandItem(root_emp)

        # Navigation behavior: clicking items selects associated page if mapped
        def on_tree_item_clicked(item, _col):
            title = item.text(0).strip()
            # Clicking Loans root toggles expand/collapse; ignore content change
            if title == "وام‌ها":
                return
            idx = (self._page_index_map or {}).get(title)
            if idx is not None:
                self.content_stack.setCurrentIndex(idx)
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

    def _logout(self):
        try:
            # Use centralized client (will inject token)
            from client.services import api_client
        except Exception:
            from .services import api_client
        try:
            api_client.post_json("http://127.0.0.1:5000/api/auth/logout", {})
        except Exception:
            pass
        # Close dashboard and return to login
        self.close()
        try:
            from client.state import session as _session
        except Exception:
            from .state import session as _session
        _session.clear_session()
        self.بازگشت_به_ورود()

    def _build_admin_users_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Search + Filters bar (top)
        filters_bar = QHBoxLayout(); filters_bar.setSpacing(8)
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("جستجو نام/نام خانوادگی")
        self.filter_department = QComboBox(); self.filter_department.setMinimumWidth(180)
        self.filter_branch = QComboBox(); self.filter_branch.setMinimumWidth(160)
        # Default options
        self.filter_department.addItem("همه دپارتمان‌ها", -1)
        self.filter_branch.addItem("همه شعب", -1)
        # Wire up live filtering
        self.search_input.textChanged.connect(self._apply_filters)
        self.filter_department.currentIndexChanged.connect(self._apply_filters)
        self.filter_branch.currentIndexChanged.connect(self._apply_filters)
        filters_bar.addWidget(self.search_input)
        filters_bar.addWidget(self.filter_department)
        filters_bar.addWidget(self.filter_branch)
        layout.addLayout(filters_bar)

        # Users Table Card
        table_card = QGroupBox("فهرست کاربران")
        table_card.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #ddd; border-radius:6px; margin-top:10px;} QGroupBox::title{subcontrol-origin: margin; subcontrol-position: top right; padding: 0 8px;}")
        table_layout = QVBoxLayout(); table_layout.setSpacing(8)

        self.tbl_users = QTableWidget(0, 8)
        self.tbl_users.setHorizontalHeaderLabels(["ID", "نام", "کدملی", "نقش", "وضعیت", "مشاهده", "ویرایش", "حذف"]) 
        self.tbl_users.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_users.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_users.setSelectionBehavior(QAbstractItemView.SelectRows)
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

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        widget.setLayout(layout)
        # Light theme, white background
        widget.setStyleSheet("QWidget{background:white;color:black;}")
        self._load_users()
        return widget

    def _load_meta(self):
        try:
            # Use centralized client to include token
            try:
                from client.services import api_client
            except Exception:
                from .services import api_client
            r = api_client.get(API_EMP_META)
            data = r.json()
        except Exception:
            self.lbl_status.setText("بارگذاری اطلاعات دپارتمان/شعبه ناموفق بود.")
            return
        # Populate top filters
        self.filter_department.clear(); self.filter_branch.clear()
        self.filter_department.addItem("همه دپارتمان‌ها", -1)
        self.filter_branch.addItem("همه شعب", -1)
        for d in data.get("departments", []):
            self.filter_department.addItem(d.get("name", ""), d.get("id"))
        for b in data.get("branches", []):
            self.filter_branch.addItem(b.get("name", ""), b.get("id"))

    def _load_users(self):
        try:
            try:
                from client.services import api_client
            except Exception:
                from .services import api_client
            r = api_client.get(API_EMP_CREATE)
            data = r.json()
        except Exception:
            self.lbl_users.setText("بارگذاری لیست کاربران ناموفق بود.")
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
        """Apply search text + department/branch filters client-side."""
        txt = (self.search_input.text() or "").strip().lower()
        dep_id = self.filter_department.currentData()
        br_id = self.filter_branch.currentData()
        def match(item):
            # name filtering: accepts first/last name parts in full_name
            if txt:
                name = (item.get("full_name") or "").lower()
                if txt not in name:
                    return False
            if dep_id not in (None, -1):
                if item.get("department_id") != dep_id:
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
            "department_id": self.cb_department.currentData(),
            "branch_id": self.cb_branch.currentData(),
            "phone": self.in_phone.text().strip(),
            "address": self.in_address.toPlainText().strip(),
            "monthly_salary": float(self.in_salary.value()),
            "status": "active" if self.cb_status.currentIndex() == 0 else "inactive",
        }
        try:
            try:
                from client.services import api_client
            except Exception:
                from .services import api_client
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
        self.setWindowTitle("ورود")
        QApplication.instance().setLayoutDirection(Qt.RightToLeft)

        self.چیدمان = QVBoxLayout(); self.چیدمان.setSpacing(14)

        title = QLabel("به سیستم مدیریت خوش آمدید")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:bold; margin-bottom:6px;")

        self.کدملی = QLineEdit(); self.کدملی.setPlaceholderText("کد ملی ۱۰ رقمی")
        self.رمز_عبور = QLineEdit(); self.رمز_عبور.setPlaceholderText("رمز عبور"); self.رمز_عبور.setEchoMode(QLineEdit.Password)

        self.دکمه_ورود = QPushButton("ورود")
        self.دکمه_ورود.setStyleSheet("QPushButton{background:#0d6efd;color:white;padding:8px 14px;border-radius:6px;} QPushButton:hover{background:#0b5ed7}")

        self.برچسب_وضعیت = QLabel(""); self.برچسب_وضعیت.setAlignment(Qt.AlignCenter)
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
                from .services.auth_service import login as auth_login
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
    """Load and apply Vazir font globally."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "fonts"))
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
