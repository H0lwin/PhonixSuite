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
            created_by_id INT NULL,
            created_by_name VARCHAR(191) NULL,
            created_by_nid VARCHAR(10) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_loans_created_by FOREIGN KEY (created_by_id) REFERENCES employees(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    
    # Add missing columns for existing tables (backward compatibility)
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'loans' AND COLUMN_NAME = 'created_by_id'
        """)
        if cur.fetchone()[0] == 0:
            cur.execute("ALTER TABLE loans ADD COLUMN created_by_id INT NULL")
            cur.execute("ALTER TABLE loans ADD CONSTRAINT fk_loans_created_by FOREIGN KEY (created_by_id) REFERENCES employees(id) ON DELETE SET NULL")
    except Exception:
        pass
    
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'loans' AND COLUMN_NAME = 'created_by_name'
        """)
        if cur.fetchone()[0] == 0:
            cur.execute("ALTER TABLE loans ADD COLUMN created_by_name VARCHAR(191) NULL")
    except Exception:
        pass
    
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'loans' AND COLUMN_NAME = 'created_by_nid'
        """)
        if cur.fetchone()[0] == 0:
            cur.execute("ALTER TABLE loans ADD COLUMN created_by_nid VARCHAR(10) NULL")
    except Exception:
        pass

    conn.commit()
    cur.close()
    conn.close()


def create_loan(data: Dict[str, Any]) -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO loans (bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date,
                           loan_status, introducer, payment_type, purchase_rate, created_by_id, created_by_name, created_by_nid)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("bank_name"), data.get("loan_type"), data.get("duration"), data.get("amount"),
            data.get("owner_full_name"), data.get("owner_phone"), data.get("visit_date"),
            data.get("loan_status", "available"), data.get("introducer"), data.get("payment_type"), data.get("purchase_rate"),
            data.get("created_by_id"), data.get("created_by_name"), data.get("created_by_nid"),
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
        "SELECT id, bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate, created_by_id, created_by_name, created_by_nid FROM loans ORDER BY id DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = [
        "id","bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate","created_by_id","created_by_name","created_by_nid"
    ]
    return [dict(zip(cols, r)) for r in rows]


def list_loans_for_user(user_role: str, user_nid: Optional[str] = None) -> List[dict]:
    """List loans based on user role and access permissions.
    - admin: sees all loans
    - employee: sees limited fields from non-purchased loans
    """
    conn = get_connection(True)
    cur = conn.cursor()
    
    if user_role == "admin":
        # Admin sees everything
        cur.execute(
            "SELECT id, bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate, created_by_id, created_by_name, created_by_nid FROM loans ORDER BY id DESC"
        )
        cols = [
            "id","bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate","created_by_id","created_by_name","created_by_nid"
        ]
    else:
        # Employee/user sees limited fields and no purchased loans
        cur.execute(
            "SELECT id, bank_name, loan_type, duration, amount, loan_status FROM loans WHERE loan_status != 'purchased' ORDER BY id DESC"
        )
        cols = ["id","bank_name","loan_type","duration","amount","loan_status"]
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def get_loan(loan_id: int) -> Optional[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate, created_by_id, created_by_name, created_by_nid FROM loans WHERE id=%s",
        (loan_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    cols = [
        "id","bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate","created_by_id","created_by_name","created_by_nid"
    ]
    return dict(zip(cols, row))


def update_loan(loan_id: int, data: Dict[str, Any]):
    # Build dynamic update
    allowed = ["bank_name","loan_type","duration","amount","owner_full_name","owner_phone","visit_date","loan_status","introducer","payment_type","purchase_rate","created_by_id","created_by_name","created_by_nid"]
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


def delete_loan(loan_id: int):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM loans WHERE id=%s", (loan_id,))
    conn.commit()
    cur.close()
    conn.close()