# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List, Tuple
from database import get_connection


def ensure_creditor_schema():
    conn = get_connection(True)
    cur = conn.cursor()

    # Base table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS creditors (
            id INT PRIMARY KEY AUTO_INCREMENT,
            loan_id INT NULL,
            full_name VARCHAR(191) NOT NULL,
            amount DECIMAL(14,2) NOT NULL,
            description VARCHAR(500) NULL,
            settlement_status ENUM('settled','unsettled') NOT NULL DEFAULT 'unsettled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_creditors_loan_id (loan_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    # Add new columns/indexes if they don't exist (for existing databases)
    # Fallback method without IF NOT EXISTS for broader MySQL compatibility
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'settlement_date'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN settlement_date DATE NULL")
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'settlement_notes'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN settlement_notes VARCHAR(500) NULL")
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'loan_id'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN loan_id INT NULL")
    except Exception:
        pass
    # New optional fields to store loan metadata on creditor
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'loan_rate'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN loan_rate DECIMAL(14,2) NULL")
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'bank_name'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN bank_name VARCHAR(191) NULL")
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND COLUMN_NAME = 'owner_phone'
        """)
        need = cur.fetchone()[0] == 0
        if need:
            cur.execute("ALTER TABLE creditors ADD COLUMN owner_phone VARCHAR(32) NULL")
    except Exception:
        pass
    try:
        cur.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'creditors' AND INDEX_NAME = 'idx_creditors_loan_id'
        """)
        need_idx = cur.fetchone()[0] == 0
        if need_idx:
            cur.execute("CREATE INDEX idx_creditors_loan_id ON creditors(loan_id)")
    except Exception:
        pass

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


def _compute_paid(conn, creditor_id: int) -> float:
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM creditor_installments WHERE creditor_id=%s", (creditor_id,))
    paid = float(cur.fetchone()[0] or 0)
    cur.close()
    return paid


def _recalc_status(conn, creditor_id: int):
    cur = conn.cursor()
    cur.execute("SELECT amount FROM creditors WHERE id=%s", (creditor_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); return
    total = float(row[0] or 0)
    paid = _compute_paid(conn, creditor_id)
    new_status = 'settled' if paid >= total and total > 0 else 'unsettled'
    cur.execute("UPDATE creditors SET settlement_status=%s WHERE id=%s", (new_status, creditor_id))
    conn.commit()
    cur.close()


def create_creditor(full_name: str, amount: float, description: str, loan_id: int | None = None,
                    loan_rate: float | None = None, bank_name: str | None = None, owner_phone: str | None = None) -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    # Insert with extended metadata when available
    cur.execute(
        """
        INSERT INTO creditors (loan_id, full_name, amount, description, loan_rate, bank_name, owner_phone)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (loan_id, full_name, amount, description, loan_rate, bank_name, owner_phone),
    )
    new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def update_creditor(creditor_id: int, data: Dict[str, Any]):
    allowed = ["full_name", "amount", "description", "settlement_status", "settlement_date", "settlement_notes"]
    fields, values = [], []
    for k in allowed:
        if k in data:
            fields.append(f"{k}=%s"); values.append(data[k])
    if not fields:
        return
    values.append(creditor_id)
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(f"UPDATE creditors SET {', '.join(fields)} WHERE id=%s", tuple(values))
    # After amount change, recalc status
    _recalc_status(conn, creditor_id)
    conn.commit(); cur.close(); conn.close()


def delete_creditor(creditor_id: int):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM creditors WHERE id=%s", (creditor_id,))
    conn.commit(); cur.close(); conn.close()


def add_installment(creditor_id: int, amount: float, pay_date: str, notes: str = None):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO creditor_installments (creditor_id, amount, pay_date, notes) VALUES (%s,%s,%s,%s)",
        (creditor_id, amount, pay_date, notes),
    )
    # Check if fully settled
    cur.execute("SELECT amount FROM creditors WHERE id=%s", (creditor_id,))
    total_row = cur.fetchone()
    total = float(total_row[0] or 0) if total_row else 0
    paid = _compute_paid(conn, creditor_id)
    if paid >= total and total > 0:
        cur.execute("UPDATE creditors SET settlement_status='settled' WHERE id=%s", (creditor_id,))
    else:
        cur.execute("UPDATE creditors SET settlement_status='unsettled' WHERE id=%s", (creditor_id,))
    conn.commit()
    cur.close()
    conn.close()


def list_creditors(status: Optional[str] = None) -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    where = ""
    vals: Tuple[Any, ...] = tuple()
    if status:
        where = " WHERE settlement_status=%s"
        vals = (status,)
    cur.execute(
        f"SELECT id, full_name, amount, description, settlement_status FROM creditors{where} ORDER BY id DESC",
        vals,
    )
    rows = cur.fetchall()
    cols = ["id","full_name","amount","description","settlement_status"]
    items = [dict(zip(cols, r)) for r in rows]
    # enrich with paid and remaining
    for it in items:
        paid = _compute_paid(conn, it["id"])  # uses its own cursor
        total = float(it.get("amount") or 0)
        it["paid_amount"] = paid
        it["remaining_amount"] = max(total - paid, 0)
    cur.close(); conn.close()
    return items


def get_creditor(creditor_id: int) -> Optional[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, full_name, amount, description, settlement_status, settlement_date, settlement_notes,
               loan_id, loan_rate, bank_name, owner_phone
        FROM creditors WHERE id=%s
        """,
        (creditor_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close(); return None
    cols = [
        "id","full_name","amount","description","settlement_status","settlement_date","settlement_notes",
        "loan_id","loan_rate","bank_name","owner_phone"
    ]
    item = dict(zip(cols, row))
    # Normalize numeric types for JSON serialization
    try:
        item["amount"] = float(item.get("amount") or 0)
    except Exception:
        item["amount"] = 0.0
    try:
        lr = item.get("loan_rate")
        item["loan_rate"] = (float(lr) if lr is not None else None)
    except Exception:
        pass
    # installments
    cur.execute(
        "SELECT id, pay_date, amount, notes FROM creditor_installments WHERE creditor_id=%s ORDER BY pay_date ASC, id ASC",
        (creditor_id,),
    )
    ins = cur.fetchall()
    item["installments"] = [
        {"id": rid, "date": str(dt), "amount": float(amt or 0), "notes": notes}
        for (rid, dt, amt, notes) in ins
    ]
    paid = sum((float(x[2] or 0) for x in ins)) if ins else 0.0
    total = float(item.get("amount") or 0)
    item["paid_amount"] = float(paid)
    item["remaining_amount"] = max(total - paid, 0)
    cur.close(); conn.close()
    return item


def settle_creditor(creditor_id: int, pay_date: str, notes: Optional[str] = None):
    conn = get_connection(True)
    cur = conn.cursor()
    # compute remaining
    cur.execute("SELECT amount FROM creditors WHERE id=%s", (creditor_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close(); return
    total = float(row[0] or 0)
    paid = _compute_paid(conn, creditor_id)
    remaining = max(total - paid, 0)
    if remaining > 0:
        cur.execute(
            "INSERT INTO creditor_installments (creditor_id, amount, pay_date, notes) VALUES (%s,%s,%s,%s)",
            (creditor_id, remaining, pay_date, notes or "Full settlement"),
        )
    cur.execute(
        "UPDATE creditors SET settlement_status='settled', settlement_date=%s, settlement_notes=%s WHERE id=%s",
        (pay_date, notes, creditor_id),
    )
    conn.commit(); cur.close(); conn.close()
