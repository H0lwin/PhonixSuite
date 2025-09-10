# -*- coding: utf-8 -*-
"""Employee model helpers (raw SQL with mysql-connector).
Fields (English names for DB):
- id INT PK AI
- full_name VARCHAR(191)
- national_id VARCHAR(10) UNIQUE
- password VARCHAR(255)  # plain text for now (prototype)
- role VARCHAR(100)
- department_id INT NULL
- branch_id INT NULL
- phone VARCHAR(32)
- address VARCHAR(500)
- monthly_salary DECIMAL(12,2) DEFAULT 0
- status ENUM('active','inactive') DEFAULT 'active'
- created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
"""
from typing import Optional, Dict, Any
from mysql.connector import Error
# Use module-local import so server/app.py can run as a script
from database import get_connection


def ensure_employee_schema():
    """Create departments, branches, and employees tables if not exist. Seed basic rows."""
    conn = get_connection(database=True)
    cur = conn.cursor()

    # Departments
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(191) UNIQUE NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    # Branches
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(191) UNIQUE NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    # Employees
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INT PRIMARY KEY AUTO_INCREMENT,
            full_name VARCHAR(191) NOT NULL,
            national_id VARCHAR(10) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(100) NOT NULL,
            department_id INT NULL,
            branch_id INT NULL,
            phone VARCHAR(32) NULL,
            address VARCHAR(500) NULL,
            monthly_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
            status ENUM('active','inactive') NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_employees_department FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
            CONSTRAINT fk_employees_branch FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    # Seed sample departments
    cur.execute("SELECT COUNT(*) FROM departments")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO departments (name) VALUES (%s)",
            [("Loans",), ("Finance",), ("HR",), ("IT",)],
        )

    # Seed sample branches
    cur.execute("SELECT COUNT(*) FROM branches")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO branches (name) VALUES (%s)",
            [("Tehran",), ("Karaj",), ("Shiraz",), ("Mashhad",)],
        )

    conn.commit()
    cur.close()
    conn.close()


def create_employee(data: Dict[str, Any]) -> int:
    """Insert employee and return new id.
    Expects keys: full_name, national_id, password, role, department_id, branch_id, phone, address, monthly_salary, status
    """
    # Hash password using bcrypt
    password = data.get("password") or ""
    try:
        import bcrypt
        hashed_pwd = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        # Fallback: store as-is if bcrypt not available (not recommended)
        hashed_pwd = password

    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO employees
            (full_name, national_id, password, role, department_id, branch_id, phone, address, monthly_salary, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("full_name"),
            data.get("national_id"),
            hashed_pwd,
            data.get("role"),
            data.get("department_id"),
            data.get("branch_id"),
            data.get("phone"),
            data.get("address"),
            data.get("monthly_salary", 0),
            data.get("status", "active"),
        ),
    )
    new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def get_departments() -> list:
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


def get_branches() -> list:
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM branches ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


def get_employee_by_national_id(national_id: str) -> Optional[dict]:
    conn = get_connection(database=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, full_name, national_id, password, role, status FROM employees WHERE national_id=%s LIMIT 1",
        (national_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "full_name": row[1],
        "national_id": row[2],
        "password": row[3],
        "role": row[4],
        "status": row[5],
    }
