# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
from database import get_connection


def ensure_loan_schema():
    conn = get_connection(True)
    cur = conn.cursor()

    # Loans
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS loans (
            id INT PRIMARY KEY AUTO_INCREMENT,
            bank_name VARCHAR(191) NOT NULL,
            loan_type VARCHAR(191) NOT NULL,
            duration VARCHAR(50) NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            owner_full_name VARCHAR(191) NOT NULL,
            owner_phone VARCHAR(32) NOT NULL,
            visit_date DATE NULL,
            loan_status ENUM('available','failed','purchased') NOT NULL DEFAULT 'available',
            introducer VARCHAR(191) NULL,
            payment_type VARCHAR(100) NULL,
            purchase_rate DECIMAL(14,2) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def create_loan(data: Dict[str, Any]) -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO loans (bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date,
                           loan_status, introducer, payment_type, purchase_rate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("bank_name"), data.get("loan_type"), data.get("duration"), data.get("amount"),
            data.get("owner_full_name"), data.get("owner_phone"), data.get("visit_date"),
            data.get("loan_status", "available"), data.get("introducer"), data.get("payment_type"), data.get("purchase_rate"),
        ),
    )
    new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def list_loans() -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate FROM loans ORDER BY id DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = [
        "id","bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_loan(loan_id: int) -> Optional[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate FROM loans WHERE id=%s",
        (loan_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    cols = [
        "id","bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate"
    ]
    return dict(zip(cols, row))


def update_loan(loan_id: int, data: Dict[str, Any]):
    # Build dynamic update
    allowed = ["bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate"]
    fields = []
    values = []
    for k in allowed:
        if k in data:
            fields.append(f"{k}=%s")
            values.append(data[k])
    if not fields:
        return
    values.append(loan_id)

    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(f"UPDATE loans SET {', '.join(fields)} WHERE id=%s", tuple(values))
    conn.commit()
    cur.close()
    conn.close()