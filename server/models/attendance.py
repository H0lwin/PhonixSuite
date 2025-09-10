# -*- coding: utf-8 -*-
from typing import Dict, Any, List
from database import get_connection


def ensure_attendance_schema():
    conn = get_connection(True)
    cur = conn.cursor()
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_emp_date (employee_id, date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    conn.commit(); cur.close(); conn.close()


def add_attendance(data: Dict[str, Any]) -> int:
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


def list_attendance(employee_id: int) -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, check_in, check_out, status, notes FROM attendance WHERE employee_id=%s ORDER BY date DESC",
        (employee_id,),
    )
    rows = cur.fetchall(); cur.close(); conn.close()
    cols = ["id","date","check_in","check_out","status","notes"]
    return [dict(zip(cols, r)) for r in rows]