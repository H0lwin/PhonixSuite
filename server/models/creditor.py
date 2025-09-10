# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
from database import get_connection


def ensure_creditor_schema():
    conn = get_connection(True)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS creditors (
            id INT PRIMARY KEY AUTO_INCREMENT,
            full_name VARCHAR(191) NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            description VARCHAR(500) NULL,
            settlement_status ENUM('settled','unsettled') NOT NULL DEFAULT 'unsettled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS creditor_installments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            creditor_id INT NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            pay_date DATE NOT NULL,
            notes VARCHAR(500) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_ci_creditor FOREIGN KEY (creditor_id) REFERENCES creditors(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def create_creditor(full_name: str, amount: float, description: str) -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO creditors (full_name, amount, description) VALUES (%s,%s,%s)",
        (full_name, amount, description),
    )
    new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def add_installment(creditor_id: int, amount: float, pay_date: str, notes: str = None):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO creditor_installments (creditor_id, amount, pay_date, notes) VALUES (%s,%s,%s,%s)",
        (creditor_id, amount, pay_date, notes),
    )
    # Check if fully settled
    cur.execute("SELECT amount FROM creditors WHERE id=%s", (creditor_id,))
    total = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM creditor_installments WHERE creditor_id=%s", (creditor_id,))
    paid = cur.fetchone()[0]
    if paid >= total:
        cur.execute("UPDATE creditors SET settlement_status='settled' WHERE id=%s", (creditor_id,))
    conn.commit()
    cur.close()
    conn.close()


def list_creditors() -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("SELECT id, full_name, amount, description, settlement_status FROM creditors ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = ["id","full_name","amount","description","settlement_status"]
    return [dict(zip(cols, r)) for r in rows]