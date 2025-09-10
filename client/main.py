# -*- coding: utf-8 -*-
import sys
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import requests
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt


سرور_آدرس = "http://127.0.0.1:5000/login"


class پنجره_خوش_آمد(QWidget):
    def __init__(self, نقش_نمایشی: str):
        super().__init__()
        self.setWindowTitle("خوش آمدید")
        چیدمان = QVBoxLayout()
        پیام = QLabel(f"خوش آمدید {نقش_نمایشی}")
        پیام.setAlignment(Qt.AlignCenter)
        چیدمان.addWidget(پیام)
        self.setLayout(چیدمان)


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


class پنجره_ورود(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ورود")
        QApplication.instance().setLayoutDirection(Qt.RightToLeft)

        self.چیدمان = QVBoxLayout()

        self.نام_کاربری = QLineEdit()
        self.نام_کاربری.setPlaceholderText("نام کاربری")

        self.رمز_عبور = QLineEdit()
        self.رمز_عبور.setPlaceholderText("رمز عبور")
        self.رمز_عبور.setEchoMode(QLineEdit.Password)

        self.دکمه_ورود = QPushButton("ورود")
        self.برچسب_وضعیت = QLabel("")
        self.برچسب_وضعیت.setAlignment(Qt.AlignCenter)

        self.چیدمان.addWidget(self.نام_کاربری)
        self.چیدمان.addWidget(self.رمز_عبور)
        self.چیدمان.addWidget(self.دکمه_ورود)
        self.چیدمان.addWidget(self.برچسب_وضعیت)

        self.setLayout(self.چیدمان)

        self.دکمه_ورود.clicked.connect(self.ارسال_ورود)

    def ارسال_ورود(self):
        نام = self.نام_کاربری.text().strip()
        گذرواژه = self.رمز_عبور.text().strip()
        if not نام or not گذرواژه:
            self.برچسب_وضعیت.setText("لطفاً نام کاربری و رمز عبور را وارد کنید.")
            return

        try:
            پاسخ = requests.post(
                سرور_آدرس,
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=json.dumps({"نام_کاربری": نام, "رمز_عبور": گذرواژه}, ensure_ascii=False).encode("utf-8"),
                timeout=10,
            )
            logging.info("Login request sent for username: %s | status_code=%s", نام, getattr(پاسخ, "status_code", None))
        except requests.RequestException:
            self.برچسب_وضعیت.setText("اتصال به سرور برقرار نشد.")
            logging.exception("Failed to reach server for login")
            return

        try:
            بدنه = پاسخ.json()
        except ValueError:
            self.برچسب_وضعیت.setText("پاسخ نامعتبر از سرور.")
            logging.error("Invalid JSON response from server: %s", پاسخ.text[:500] if hasattr(پاسخ, 'text') else 'No text')
            return

        وضعیت = بدنه.get("وضعیت")
        if وضعیت == "موفق":
            نقش_نمایشی = بدنه.get("نقش", "کاربر")
            logging.info("Login success for username: %s | role=%s", نام, نقش_نمایشی)
            self.پنجره_خوش_آمد = پنجره_خوش_آمد(نقش_نمایشی)
            self.پنجره_خوش_آمد.resize(320, 160)
            self.پنجره_خوش_آمد.show()
            self.hide()
        else:
            پیام = بدنه.get("پیام", "نام کاربری یا رمز عبور نادرست است.")
            self.برچسب_وضعیت.setText(پیام)
            logging.warning("Login failed for username: %s | message=%s", نام, پیام)


def main():
    configure_logging()
    برنامه = QApplication(sys.argv)
    برنامه.setLayoutDirection(Qt.RightToLeft)
    پنجره = پنجره_ورود()
    پنجره.resize(360, 200)
    پنجره.show()
    sys.exit(برنامه.exec())


if __name__ == "__main__":
    main()


