# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QDialogButtonBox

# Color palette (Bootstrap-like)
PRIMARY = "#0d6efd"; PRIMARY_HOVER = "#0b5ed7"
SECONDARY = "#6c757d"; SECONDARY_HOVER = "#5c636a"
DANGER = "#dc3545"; DANGER_HOVER = "#bb2d3b"

_BASE = "color:white;padding:6px 12px;border-radius:6px;"

def _btn_style(bg: str, hover: str) -> str:
    return (
        f"QPushButton{{background:{bg};{_BASE}}} "
        f"QPushButton:hover{{background:{hover}}}"
    )


def style_dialog_buttons(buttons: QDialogButtonBox) -> None:
    """Apply consistent styles to common dialog buttons.

    - Save / OK / Yes: Primary (blue)
    - Cancel / Close / No: Secondary (gray)
    - Destructive role (if any): Danger (red)
    """
    mapping = {
        QDialogButtonBox.Save: _btn_style(PRIMARY, PRIMARY_HOVER),
        QDialogButtonBox.Ok: _btn_style(PRIMARY, PRIMARY_HOVER),
        QDialogButtonBox.Yes: _btn_style(PRIMARY, PRIMARY_HOVER),
        QDialogButtonBox.Cancel: _btn_style(SECONDARY, SECONDARY_HOVER),
        QDialogButtonBox.Close: _btn_style(SECONDARY, SECONDARY_HOVER),
        QDialogButtonBox.No: _btn_style(SECONDARY, SECONDARY_HOVER),
    }
    # Style by standard buttons if present
    for std, style in mapping.items():
        btn = buttons.button(std)
        if btn:
            btn.setStyleSheet(style)
    # Ensure any DestructiveRole buttons are styled as danger
    for btn in buttons.buttons():
        try:
            role = buttons.buttonRole(btn)
        except Exception:
            role = None
        if role == QDialogButtonBox.DestructiveRole:
            btn.setStyleSheet(_btn_style(DANGER, DANGER_HOVER))