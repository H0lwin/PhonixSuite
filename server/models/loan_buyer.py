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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_lb_loan FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )

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
                                 processing_status, notes, loan_id, broker, sale_price, sale_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data.get("first_name"), data.get("last_name"), data.get("national_id"), data.get("phone"),
            data.get("requested_amount"), data.get("bank_agent"), data.get("visit_date"),
            data.get("processing_status", "request_registered"), data.get("notes"), data.get("loan_id"),
            data.get("broker"), data.get("sale_price"), data.get("sale_type"),
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
    # If status changed, add history
    if "processing_status" in data:
        _insert_status(cur, buyer_id, data["processing_status"], data.get("notes"))
    conn.commit()
    cur.close()
    conn.close()


def list_loan_buyers_for_user(user_role: str, username: Optional[str]) -> List[dict]:
    conn = get_connection(True)
    cur = conn.cursor()
    if user_role == "broker" and username:
        cur.execute(
            "SELECT id, first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, loan_id, broker, sale_price, sale_type FROM loan_buyers WHERE broker=%s ORDER BY id DESC",
            (username,),
        )
    else:
        cur.execute(
            "SELECT id, first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, loan_id, broker, sale_price, sale_type FROM loan_buyers ORDER BY id DESC"
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = ["id","first_name","last_name","national_id","phone","requested_amount","bank_agent","visit_date","processing_status","loan_id","broker","sale_price","sale_type"]
    return [dict(zip(cols, r)) for r in rows]