# -*- coding: utf-8 -*-
"""Branch model helpers.
Provides ensure_branch_schema and basic CRUD utilities for branches.
"""
from typing import List, Dict, Any, Optional
from database import get_connection


def ensure_branch_schema():
    """Ensure branches table has required columns: name, location, manager_id.
    Existing installs may have only `name`; we attempt ALTERs guarded by try/except.
    """
    conn = get_connection(database=True)
    cur = conn.cursor()
    # Base table (created by ensure_employee_schema, but create if missing)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(191) UNIQUE NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    # Add columns if not present
    try:
        cur.execute("ALTER TABLE branches ADD COLUMN location VARCHAR(255) NULL")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE branches ADD COLUMN manager_id INT NULL")
    except Exception:
        pass
    try:
        cur.execute(
            "ALTER TABLE branches ADD CONSTRAINT fk_branches_manager FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL"
        )
    except Exception:
        pass
    conn.commit(); cur.close(); conn.close()


def list_branches_with_counts() -> List[Dict[str, Any]]:
    conn = get_connection(database=True)
    cur = conn.cursor()
    # LEFT JOIN to count employees per branch
    cur.execute(
        """
        SELECT b.id, b.name, COALESCE(b.location, ''), b.manager_id,
               COUNT(e.id) AS emp_count
        FROM branches b
        LEFT JOIN employees e ON e.branch_id = b.id
        GROUP BY b.id, b.name, b.location, b.manager_id
        ORDER BY b.name
        """
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "name": r[1], "location": r[2], "manager_id": r[3], "employee_count": int(r[4] or 0)}
        for r in rows
    ]


def create_branch(name: str, location: Optional[str], manager_id: Optional[int]) -> int:
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO branches (name, location, manager_id) VALUES (%s,%s,%s)",
        (name, location, manager_id)
    )
    new_id = cur.lastrowid
    conn.commit(); cur.close(); conn.close()
    return int(new_id)


def delete_branch(branch_id: int):
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute("DELETE FROM branches WHERE id=%s", (branch_id,))
    conn.commit(); cur.close(); conn.close()


def get_branch_employees(branch_id: int) -> List[Dict[str, Any]]:
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, full_name, role, status FROM employees WHERE branch_id=%s ORDER BY full_name
        """,
        (branch_id,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "full_name": r[1], "role": r[2], "status": r[3]}
        for r in rows
    ]