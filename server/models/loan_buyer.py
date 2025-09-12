# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
from database import get_connection


def ensure_loan_buyer_schema():
    conn = get_connection(True)
    cur = conn.cursor()

    # Loan buyers
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS loan_buyers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            national_id VARCHAR(10) NOT NULL,
            phone VARCHAR(32) NOT NULL,
            requested_amount DECIMAL(14,2) NULL,
            bank_agent VARCHAR(191) NULL,
            visit_date DATE NULL,
            processing_status ENUM('request_registered','under_review','rights_transfer','bank_validation','loan_paid','guarantor_issue','borrower_issue') NOT NULL DEFAULT 'request_registered',
            notes TEXT NULL,
            loan_id INT NULL,
            broker VARCHAR(191) NULL,
            sale_price DECIMAL(14,2) NULL,
            sale_type ENUM('cash','installment') NULL,
            created_by_name VARCHAR(191) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_lb_loan FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    # Ensure created_by_name exists (migration for older tables)
    try:
        cur.execute("SHOW COLUMNS FROM loan_buyers LIKE 'created_by_name'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE loan_buyers ADD COLUMN created_by_name VARCHAR(191) NULL AFTER sale_type")
    except Exception:
        pass

    # Status history
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS loan_buyer_status_history (
            id INT PRIMARY KEY AUTO_INCREMENT,
            loan_buyer_id INT NOT NULL,
            status ENUM('request_registered','under_review','rights_transfer','bank_validation','loan_paid','guarantor_issue','borrower_issue') NOT NULL,
            note TEXT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_lbh_buyer FOREIGN KEY (loan_buyer_id) REFERENCES loan_buyers(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def _insert_status(cur, buyer_id: int, status: str, note: str = None):
    cur.execute(
        "INSERT INTO loan_buyer_status_history (loan_buyer_id, status, note) VALUES (%s,%s,%s)",
        (buyer_id, status, note),
    )


def create_loan_buyer(data: Dict[str, Any]) -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO loan_buyers (first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date,
                                 processing_status, notes, loan_id, broker, sale_price, sale_type, created_by_name)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("first_name"), data.get("last_name"), data.get("national_id"), data.get("phone"),
            data.get("requested_amount"), data.get("bank_agent"), data.get("visit_date"),
            data.get("processing_status", "request_registered"), data.get("notes"), data.get("loan_id"),
            data.get("broker"), data.get("sale_price"), data.get("sale_type"), data.get("created_by_name"),
        ),
    )
    buyer_id = cur.lastrowid
    _insert_status(cur, buyer_id, data.get("processing_status", "request_registered"), data.get("notes"))
    conn.commit()
    cur.close()
    conn.close()
    return buyer_id


def update_loan_buyer(buyer_id: int, data: Dict[str, Any]):
    allowed = [
        "first_name","last_name","national_id","phone","requested_amount","bank_agent","visit_date",
        "processing_status","notes","loan_id","sale_price","sale_type"
    ]
    fields, values = [], []
    for k in allowed:
        if k in data:
            fields.append(f"{k}=%s")
            values.append(data[k])
    if not fields:
        return
    values.append(buyer_id)

    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(f"UPDATE loan_buyers SET {', '.join(fields)} WHERE id=%s", tuple(values))
    # If status changed, add history and handle business rules
    if "processing_status" in data:
        _insert_status(cur, buyer_id, data["processing_status"], data.get("notes"))
        # If completed (loan paid), mark related loan as sold/purchased
        if data.get("processing_status") == "loan_paid":
            try:
                cur.execute("SELECT loan_id FROM loan_buyers WHERE id=%s", (buyer_id,))
                row = cur.fetchone()
                loan_id = row[0] if row else None
                if loan_id:
                    # Use service to apply side effects (auto-creates creditor)
                    from services.loan_service import update_loan_with_side_effects
                    update_loan_with_side_effects(loan_id, {"loan_status": "purchased"})
            except Exception:
                pass
    conn.commit()
    cur.close()
    conn.close()


def list_loan_buyers_for_user(user_role: str, username: Optional[str]) -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    if user_role == "broker" and username:
        cur.execute(
            "SELECT id, first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, loan_id, broker, sale_price, sale_type, created_by_name, created_at, updated_at FROM loan_buyers WHERE broker=%s ORDER BY id DESC",
            (username,),
        )
    else:
        cur.execute(
            "SELECT id, first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, loan_id, broker, sale_price, sale_type, created_by_name, created_at, updated_at FROM loan_buyers ORDER BY id DESC"
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = ["id","first_name","last_name","national_id","phone","requested_amount","bank_agent","visit_date","processing_status","loan_id","broker","sale_price","sale_type","created_by_name","created_at","updated_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_loan_buyer(buyer_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, loan_id, broker, sale_price, sale_type, notes, created_at, updated_at FROM loan_buyers WHERE id=%s",
        (buyer_id,)
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return None
    cols = ["id","first_name","last_name","national_id","phone","requested_amount","bank_agent","visit_date","processing_status","loan_id","broker","sale_price","sale_type","notes","created_at","updated_at"]
    return dict(zip(cols, row))


def get_loan_buyer_history(buyer_id: int) -> List[Dict[str, Any]]:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        "SELECT status, note, changed_at FROM loan_buyer_status_history WHERE loan_buyer_id=%s ORDER BY changed_at ASC",
        (buyer_id,)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"status": r[0], "note": r[1], "changed_at": r[2]} for r in rows]


def delete_loan_buyer(buyer_id: int):
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM loan_buyers WHERE id=%s", (buyer_id,))
    conn.commit(); cur.close(); conn.close()