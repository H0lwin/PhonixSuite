# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class DashboardView(QWidget):
    """Simple placeholder dashboard view."""

    def __init__(self, display_name: str, role: str):
        super().__init__()
        self.setWindowTitle("داشبورد")
        layout = QVBoxLayout()
        title = QLabel(f"خوش آمدید، {display_name} ({'مدیر' if role == 'admin' else 'کاربر'})")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(QLabel("این یک داشبورد نمونه است."))
        self.setLayout(layout)
