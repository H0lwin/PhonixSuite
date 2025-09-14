# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time, timedelta
from database import get_connection


# ----- Schema -----

def ensure_attendance_schema():
    """Create/upgrade attendance daily summary and session tables if not exist.
    - attendance: per-day rollup (first check_in, last check_out, status, total_seconds)
    - attendance_sessions: multiple intervals per day (check_in..check_out)
    """
    conn = get_connection(True)
    cur = conn.cursor()

    # Daily summary (kept for quick reads and compatibility)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INT PRIMARY KEY AUTO_INCREMENT,
            employee_id INT NOT NULL,
            date DATE NOT NULL,
            check_in TIME NULL,
            check_out TIME NULL,
            status ENUM('present','absent','leave','mission') NOT NULL DEFAULT 'present',
            notes VARCHAR(500) NULL,
            total_seconds INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_emp_date (employee_id, date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    # Upgrade existing attendance table: add columns if missing
    try:
        cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='attendance' AND COLUMN_NAME='total_seconds'")
        if int(cur.fetchone()[0] or 0) == 0:
            cur.execute("ALTER TABLE attendance ADD COLUMN total_seconds INT NOT NULL DEFAULT 0")
        cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='attendance' AND COLUMN_NAME='updated_at'")
        if int(cur.fetchone()[0] or 0) == 0:
            cur.execute("ALTER TABLE attendance ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    except Exception:
        # Best-effort upgrade; ignore if INFORMATION_SCHEMA not accessible or MySQL variant
        pass

    # Session intervals
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            employee_id INT NOT NULL,
            date DATE NOT NULL,
            check_in TIME NOT NULL,
            check_out TIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_emp_date (employee_id, date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    conn.commit(); cur.close(); conn.close()


# ----- Helpers -----

_def_now_time = lambda: datetime.now().time().replace(microsecond=0)
_def_today = lambda: datetime.now().date()


def _serialize_date(d: Optional[date]) -> Optional[str]:
    if d is None:
        return None
    return d.isoformat()


def _serialize_time(t: Optional[Any]) -> Optional[str]:
    """Convert DB time values to HH:MM:SS string.
    MySQL connector may return time as datetime.time or datetime.timedelta.
    """
    if t is None:
        return None
    # datetime.time
    if isinstance(t, time):
        return t.replace(microsecond=0).isoformat()
    # timedelta (e.g., from TIME columns)
    if isinstance(t, timedelta):
        total_seconds = int(t.total_seconds())
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    # Fallback to string
    return str(t)


def _ensure_daily_row(conn, employee_id: int, day: date) -> None:
    """Ensure a daily summary row exists; create as 'present' when first seen."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM attendance WHERE employee_id=%s AND date=%s",
        (employee_id, day),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO attendance (employee_id, date, status) VALUES (%s,%s,'present')",
            (employee_id, day),
        )
        conn.commit()
    cur.close()


def _recompute_daily_rollup(conn, employee_id: int, day: date) -> None:
    """Recompute first check_in, last check_out, and total_seconds from sessions."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            MIN(check_in) AS first_in,
            MAX(check_out) AS last_out,
            SUM(CASE WHEN check_out IS NOT NULL THEN TIME_TO_SEC(TIMEDIFF(check_out, check_in)) ELSE 0 END) AS total_sec,
            COUNT(*) AS cnt
        FROM attendance_sessions
        WHERE employee_id=%s AND date=%s
        """,
        (employee_id, day),
    )
    first_in, last_out, total_sec, cnt = cur.fetchone() or (None, None, 0, 0)
    # Create daily row if needed
    _ensure_daily_row(conn, employee_id, day)
    # If there are no sessions, mark absent; else present
    status = 'absent' if (cnt or 0) == 0 else 'present'
    cur.execute(
        """
        UPDATE attendance
        SET check_in=%s, check_out=%s, total_seconds=%s, status=%s
        WHERE employee_id=%s AND date=%s
        """,
        (first_in, last_out, int(total_sec or 0), status, employee_id, day),
    )
    conn.commit(); cur.close()


# ----- CRUD / Actions -----


def add_attendance(data: Dict[str, Any]) -> int:
    """Backward-compatible insert (single-row). Prefer using check_in/check_out endpoints.
    Kept to avoid breaking existing callers.
    """
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO attendance (employee_id, date, check_in, check_out, status, notes)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("employee_id"), data.get("date"), data.get("check_in"), data.get("check_out"), data.get("status", "present"), data.get("notes")
        ),
    )
    new_id = cur.lastrowid
    conn.commit(); cur.close(); conn.close()
    return new_id


def check_in(employee_id: int, day: Optional[date] = None, t: Optional[time] = None) -> int:
    """Create a new session with check_in at time t (default now). Ensures daily row exists.
    Returns session id.
    """
    day = day or _def_today()
    t = t or _def_now_time()
    conn = get_connection(True)
    cur = conn.cursor()
    _ensure_daily_row(conn, employee_id, day)
    cur.execute(
        "INSERT INTO attendance_sessions (employee_id, date, check_in) VALUES (%s,%s,%s)",
        (employee_id, day, t),
    )
    sid = cur.lastrowid
    conn.commit()
    cur.close()
    # Recompute rollup (first_in etc.)
    _recompute_daily_rollup(conn, employee_id, day)
    conn.close()
    return sid


def check_out(employee_id: int, day: Optional[date] = None, t: Optional[time] = None) -> Optional[int]:
    """Close the latest open session (NULL check_out) for the employee/day. Returns affected session id or None.
    If there is no open session, returns None (no-op).
    """
    day = day or _def_today()
    t = t or _def_now_time()
    conn = get_connection(True)
    cur = conn.cursor()
    # Find latest open session for this day
    cur.execute(
        """
        SELECT id FROM attendance_sessions
        WHERE employee_id=%s AND date=%s AND check_out IS NULL
        ORDER BY id DESC LIMIT 1
        """,
        (employee_id, day),
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return None
    sid = int(row[0])
    cur2 = conn.cursor()
    cur2.execute(
        "UPDATE attendance_sessions SET check_out=%s WHERE id=%s",
        (t, sid),
    )
    conn.commit(); cur2.close(); cur.close()
    # Recompute rollup
    _recompute_daily_rollup(conn, employee_id, day)
    conn.close()
    return sid


def list_attendance(employee_id: int) -> List[dict]:
    """List per-day attendance (summary) for an employee ordered by date desc."""
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, date, check_in, check_out, status, total_seconds, notes
        FROM attendance
        WHERE employee_id=%s
        ORDER BY date DESC
        """,
        (employee_id,),
    )
    rows = cur.fetchall(); cur.close(); conn.close()
    cols = ["id","date","check_in","check_out","status","total_seconds","notes"]
    items: List[dict] = []
    for r in rows:
        d = dict(zip(cols, r))
        d["date"] = _serialize_date(d.get("date"))
        d["check_in"] = _serialize_time(d.get("check_in"))
        d["check_out"] = _serialize_time(d.get("check_out"))
        d["total_seconds"] = int(d.get("total_seconds") or 0)
        items.append(d)
    return items


def list_attendance_admin(
    employee_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[dict]:
    """Admin listing with optional filters; returns daily rows joined with employee name.
    - If no sessions for a day, there won't be a row unless explicitly constructed; admin UI can query a single date to infer 'absent'.
    """
    conn = get_connection(True)
    cur = conn.cursor()
    sql = [
        """
        SELECT a.employee_id, e.full_name, a.date, a.check_in, a.check_out, a.total_seconds, a.status
        FROM attendance a
        JOIN employees e ON e.id = a.employee_id
        """
    ]
    where = []
    params: List[Any] = []
    if employee_id:
        where.append("a.employee_id=%s"); params.append(employee_id)
    if date_from:
        where.append("a.date >= %s"); params.append(date_from)
    if date_to:
        where.append("a.date <= %s"); params.append(date_to)
    if where:
        sql.append("WHERE "+ " AND ".join(where))
    sql.append("ORDER BY a.date DESC, a.employee_id ASC")
    q = "\n".join(sql)
    cur.execute(q, tuple(params))
    rows = cur.fetchall(); cur.close(); conn.close()
    cols = ["employee_id","full_name","date","check_in","check_out","total_seconds","status"]
    items: List[dict] = []
    for r in rows:
        d = dict(zip(cols, r))
        d["date"] = _serialize_date(d.get("date"))
        d["check_in"] = _serialize_time(d.get("check_in"))
        d["check_out"] = _serialize_time(d.get("check_out"))
        d["total_seconds"] = int(d.get("total_seconds") or 0)
        items.append(d)
    return items


def get_daily_status(employee_id: int, day: date) -> dict:
    """Return a single-day status; if no sessions and no row, returns 'absent'."""
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT date, check_in, check_out, total_seconds, status FROM attendance WHERE employee_id=%s AND date=%s",
        (employee_id, day),
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return {
            "employee_id": employee_id,
            "date": _serialize_date(day),
            "check_in": None,
            "check_out": None,
            "total_seconds": 0,
            "status": "absent",
        }
    return {
        "employee_id": employee_id,
        "date": _serialize_date(row[0]),
        "check_in": _serialize_time(row[1]),
        "check_out": _serialize_time(row[2]),
        "total_seconds": int(row[3] or 0),
        "status": row[4] or "present",
    }