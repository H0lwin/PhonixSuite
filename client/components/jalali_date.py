# -*- coding: utf-8 -*-
# Simple Jalali (Shamsi) date picker and conversion utilities for PySide6
from __future__ import annotations
from typing import Optional, Tuple
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QDialog, QVBoxLayout,
    QComboBox, QDialogButtonBox, QLabel
)

# ---- Gregorian <-> Jalali conversion helpers (algorithms based on common implementations) ----
# Returns (jy, jm, jd)
def gregorian_to_jalali(gy: int, gm: int, gd: int) -> Tuple[int, int, int]:
    g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365*gy2 + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400
    g_day_no += g_d_m[gm2] + gd2
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no = j_day_no % 12053
    jy = 979 + 33*j_np + 4*(j_day_no//1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 366)//365 + 1
        j_day_no = (j_day_no - 366) % 365
    if j_day_no < 186:
        jm = 1 + j_day_no//31
        jd = 1 + (j_day_no % 31)
    else:
        jm = 7 + (j_day_no - 186)//30
        jd = 1 + ((j_day_no - 186) % 30)
    return jy, jm, jd

# Returns (gy, gm, gd)
def jalali_to_gregorian(jy: int, jm: int, jd: int) -> Tuple[int, int, int]:
    jy2 = jy - 979
    j_day_no = 365*jy2 + (jy2//33)*8 + ((jy2 % 33)+3)//4
    if jm < 7:
        j_day_no += (jm - 1)*31
    else:
        j_day_no += (jm - 7)*30 + 186
    j_day_no += jd - 1
    g_day_no = j_day_no + 79
    gy = 1600 + 400*(g_day_no//146097)
    g_day_no %= 146097
    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100*(g_day_no//36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False
    gy += 4*(g_day_no//1461)
    g_day_no %= 1461
    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no//365
        g_day_no %= 365
    gd_m = [0,31, (29 if not leap else 29), 31,30,31,30,31,31,30,31,30,31]
    # compute month
    gm = 0
    i = 1
    g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
    # Expand daily walk
    months_days = [31, 29 if ((gy%4==0 and gy%100!=0) or (gy%400==0)) else 28, 31,30,31,30,31,31,30,31,30,31]
    gm = 1
    while gm <= 12 and g_day_no >= months_days[gm-1]:
        g_day_no -= months_days[gm-1]
        gm += 1
    gd = int(g_day_no) + 1
    return gy, gm, gd

# ---- Jalali Date Picker ----
PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]

def jalali_month_days(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    # Esfand: leap if remainder of (jy-474) % 2820 < 683 yields leap logic
    # Approximation using 33-year cycles as above conversion uses
    # Use Gregorian convert round-trip to compute last day in Esfand
    gy, gm, gd = jalali_to_gregorian(jy, 12, 29)
    jy2, jm2, jd2 = gregorian_to_jalali(gy, gm, gd)
    return 30 if (jd2 == 29) else 29

class JalaliDatePickerDialog(QDialog):
    def __init__(self, parent=None, jy: int = 1400, jm: int = 1, jd: int = 1):
        super().__init__(parent)
        self.setWindowTitle("انتخاب تاریخ (جلالی)")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(480)
        v = QVBoxLayout(self); v.setContentsMargins(12,12,12,12); v.setSpacing(12)
        row = QHBoxLayout(); row.setSpacing(8); v.addLayout(row)
        self.cb_year = QComboBox(); self.cb_month = QComboBox(); self.cb_day = QComboBox()
        # Uniform combo styling via dialog stylesheet
        self.setStyleSheet("""
            QLabel{font-size:13px;}
            QComboBox{padding:8px 10px; min-height:36px; border:1px solid #ced4da; border-radius:6px; font-size:13px;}
            QDialog QPushButton{min-width:100px;padding:6px 12px;border-radius:6px;}
        """)
        # Year range (1390..1450)
        for y in range(1390, 1451):
            self.cb_year.addItem(str(y), y)
        self.cb_month.addItems(PERSIAN_MONTHS)
        row.addWidget(QLabel("سال")); row.addWidget(self.cb_year)
        row.addWidget(QLabel("ماه")); row.addWidget(self.cb_month)
        row.addWidget(QLabel("روز")); row.addWidget(self.cb_day)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        def refill_days():
            y = self.cb_year.currentData()
            m = self.cb_month.currentIndex() + 1
            days = jalali_month_days(y, m)
            cur = self.cb_day.currentText()
            self.cb_day.blockSignals(True)
            self.cb_day.clear()
            for d in range(1, days+1):
                self.cb_day.addItem(str(d), d)
            # try keep previous day
            idx = self.cb_day.findText(cur)
            if idx >= 0: self.cb_day.setCurrentIndex(idx)
            self.cb_day.blockSignals(False)
        self.cb_year.currentIndexChanged.connect(refill_days)
        self.cb_month.currentIndexChanged.connect(refill_days)
        # init values
        yi = self.cb_year.findData(jy)
        if yi >= 0: self.cb_year.setCurrentIndex(yi)
        self.cb_month.setCurrentIndex(max(0, jm-1))
        refill_days()
        di = self.cb_day.findData(jd)
        if di >= 0: self.cb_day.setCurrentIndex(di)

    def get_jalali(self) -> Tuple[int,int,int]:
        return (self.cb_year.currentData(), self.cb_month.currentIndex()+1, self.cb_day.currentData())

class JalaliDateEdit(QWidget):
    """
    Lightweight composite widget: read-only line edit + button that opens a Jalali date picker dialog.
    Exposes helpers to set/get date using Jalali or Gregorian (QDate or ISO string).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        h = QHBoxLayout(self); h.setContentsMargins(0,0,0,0); h.setSpacing(6)
        self.le = QLineEdit(); self.le.setReadOnly(True)
        self.le.setMinimumHeight(34)
        self.le.setStyleSheet("QLineEdit{padding:8px 10px; border:1px solid #ced4da; border-radius:6px; font-size:13px;}")
        self.btn = QPushButton("📅"); self.btn.setFixedWidth(40)
        self.btn.setStyleSheet("QPushButton{padding:6px 10px; border:1px solid #ced4da; border-radius:6px; background:#f8f9fa;} QPushButton:hover{background:#e9ecef}")
        h.addWidget(self.le, 1); h.addWidget(self.btn, 0)
        self.btn.clicked.connect(self._open_picker)
        # default
        self._jy, self._jm, self._jd = 1400, 1, 1
        self._sync_text()

    def _sync_text(self):
        self.le.setText(f"{self._jy:04d}-{self._jm:02d}-{self._jd:02d}")

    def _open_picker(self):
        dlg = JalaliDatePickerDialog(self, self._jy, self._jm, self._jd)
        if dlg.exec():
            self._jy, self._jm, self._jd = dlg.get_jalali()
            self._sync_text()

    # -- public helpers --
    def set_from_gregorian(self, qdate: QDate):
        if not qdate or not qdate.isValid():
            return
        jy, jm, jd = gregorian_to_jalali(qdate.year(), qdate.month(), qdate.day())
        self._jy, self._jm, self._jd = jy, jm, jd
        self._sync_text()

    def set_from_gregorian_str(self, iso: str):
        try:
            y, m, d = map(int, iso.split("-"))
            self.set_from_gregorian(QDate(y, m, d))
        except Exception:
            pass

    def get_gregorian_qdate(self) -> Optional[QDate]:
        try:
            gy, gm, gd = jalali_to_gregorian(self._jy, self._jm, self._jd)
            return QDate(gy, gm, gd)
        except Exception:
            return None

    def get_gregorian_iso(self) -> Optional[str]:
        qd = self.get_gregorian_qdate()
        if not qd:
            return None
        return qd.toString("yyyy-MM-dd")

    def text(self) -> str:
        return self.le.text()

# ---- Datetime to Jalali string helper ----

def to_jalali_dt_str(dt_val) -> str:
    """Convert a datetime-like value or string to Jalali date with HH:MM.
    Accepts formats like 'YYYY-MM-DD HH:MM:SS' or ISO strings; falls back to input str.
    """
    try:
        from datetime import datetime
        if hasattr(dt_val, 'year') and hasattr(dt_val, 'month') and hasattr(dt_val, 'day'):
            y, m, d = dt_val.year, dt_val.month, dt_val.day
            hh = getattr(dt_val, 'hour', 0); mm = getattr(dt_val, 'minute', 0)
        else:
            s = str(dt_val)
            # Try common MySQL/ISO formats
            dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
                try:
                    dt = datetime.strptime(s[:19], fmt)
                    break
                except Exception:
                    continue
            if dt is None:
                try:
                    dt = datetime.fromisoformat(s.replace('Z',''))
                except Exception:
                    return s
            y, m, d = dt.year, dt.month, dt.day
            hh, mm = dt.hour, dt.minute
        jy, jm, jd = gregorian_to_jalali(y, m, d)
        return f"{jy:04d}-{jm:02d}-{jd:02d} {hh:02d}:{mm:02d}"
    except Exception:
        return str(dt_val)