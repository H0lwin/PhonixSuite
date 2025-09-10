# -*- coding: utf-8 -*-
from typing import List, Dict
from database import get_connection


def ensure_finance_schema():
    conn = get_connection(True)
    cur = conn.cursor()
    # Revenue and Expense
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS revenues (
            id INT PRIMARY KEY AUTO_INCREMENT,
            source VARCHAR(191) NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            ref_id INT NULL,
            ref_type VARCHAR(50) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INT PRIMARY KEY AUTO_INCREMENT,
            source VARCHAR(191) NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            ref_id INT NULL,
            ref_type VARCHAR(50) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def add_revenue(source: str, amount: float, ref_id=None, ref_type=None):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("INSERT INTO revenues (source, amount, ref_id, ref_type) VALUES (%s,%s,%s,%s)", (source, amount, ref_id, ref_type))
    conn.commit()
    cur.close()
    conn.close()


def add_expense(source: str, amount: float, ref_id=None, ref_type=None):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses (source, amount, ref_id, ref_type) VALUES (%s,%s,%s,%s)", (source, amount, ref_id, ref_type))
    conn.commit()
    cur.close()
    conn.close()


def monthly_summary(year: int, month: int) -> Dict[str, float]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s", (year, month))
    total_rev = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s", (year, month))
    total_exp = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {"total_revenues": float(total_rev or 0), "total_expenses": float(total_exp or 0)}