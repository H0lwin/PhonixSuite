# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from datetime import datetime, timedelta
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


def get_total_unpaid_creditors() -> float:
    """Calculate total unpaid loan amounts from unsettled creditors"""
    conn = get_connection(True)
    cur = conn.cursor()
    
    # Get all unsettled creditors with their amounts and paid installments
    cur.execute(
        """
        SELECT c.id, c.amount, COALESCE(SUM(ci.amount), 0) as paid_amount
        FROM creditors c
        LEFT JOIN creditor_installments ci ON c.id = ci.creditor_id
        WHERE c.settlement_status = 'unsettled'
        GROUP BY c.id, c.amount
        """
    )
    
    rows = cur.fetchall()
    total_unpaid = 0.0
    
    for creditor_id, total_amount, paid_amount in rows:
        remaining = float(total_amount or 0) - float(paid_amount or 0)
        if remaining > 0:
            total_unpaid += remaining
    
    cur.close()
    conn.close()
    return total_unpaid


def get_monthly_revenue_with_comparison(year: int, month: int) -> Dict[str, any]:
    """Get current month revenue (manual + auto-sale margin) with comparison to previous month"""
    conn = get_connection(True)
    cur = conn.cursor()

    # Manual revenues
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (year, month)
    )
    manual_current = float(cur.fetchone()[0] or 0)

    prev_date = datetime(year, month, 1) - timedelta(days=1)
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (prev_date.year, prev_date.month)
    )
    manual_prev = float(cur.fetchone()[0] or 0)

    # Auto revenue from sold loans (sale_price - purchase_rate) by buyer updated_at
    cur.execute(
        """
        SELECT COALESCE(SUM(lb.sale_price - l.purchase_rate), 0)
        FROM loan_buyers lb
        LEFT JOIN loans l ON lb.loan_id = l.id
        WHERE lb.processing_status = 'loan_paid'
          AND lb.sale_price IS NOT NULL AND l.purchase_rate IS NOT NULL
          AND YEAR(lb.updated_at)=%s AND MONTH(lb.updated_at)=%s
        """,
        (year, month)
    )
    auto_current = float(cur.fetchone()[0] or 0)

    cur.execute(
        """
        SELECT COALESCE(SUM(lb.sale_price - l.purchase_rate), 0)
        FROM loan_buyers lb
        LEFT JOIN loans l ON lb.loan_id = l.id
        WHERE lb.processing_status = 'loan_paid'
          AND lb.sale_price IS NOT NULL AND l.purchase_rate IS NOT NULL
          AND YEAR(lb.updated_at)=%s AND MONTH(lb.updated_at)=%s
        """,
        (prev_date.year, prev_date.month)
    )
    auto_prev = float(cur.fetchone()[0] or 0)

    current_revenue = manual_current + auto_current
    prev_revenue = manual_prev + auto_prev

    percentage_change = 0.0
    if prev_revenue > 0:
        percentage_change = ((current_revenue - prev_revenue) / prev_revenue) * 100
    elif current_revenue > 0:
        percentage_change = 100.0

    cur.close()
    conn.close()

    return {
        "amount": current_revenue,
        "percentage_change": round(percentage_change, 1)
    }


def get_net_profit_with_comparison(year: int, month: int) -> Dict[str, any]:
    """Net profit = (manual revenue + auto-sale margin) - expenses, with comparison."""
    conn = get_connection(True)
    cur = conn.cursor()

    # Manual revenues
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (year, month)
    )
    manual_current = float(cur.fetchone()[0] or 0)

    prev_date = datetime(year, month, 1) - timedelta(days=1)
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (prev_date.year, prev_date.month)
    )
    manual_prev = float(cur.fetchone()[0] or 0)

    # Auto revenue from sold loans (sale_price - purchase_rate)
    cur.execute(
        """
        SELECT COALESCE(SUM(lb.sale_price - l.purchase_rate), 0)
        FROM loan_buyers lb
        LEFT JOIN loans l ON lb.loan_id = l.id
        WHERE lb.processing_status = 'loan_paid'
          AND lb.sale_price IS NOT NULL AND l.purchase_rate IS NOT NULL
          AND YEAR(lb.updated_at)=%s AND MONTH(lb.updated_at)=%s
        """,
        (year, month)
    )
    auto_current = float(cur.fetchone()[0] or 0)

    cur.execute(
        """
        SELECT COALESCE(SUM(lb.sale_price - l.purchase_rate), 0)
        FROM loan_buyers lb
        LEFT JOIN loans l ON lb.loan_id = l.id
        WHERE lb.processing_status = 'loan_paid'
          AND lb.sale_price IS NOT NULL AND l.purchase_rate IS NOT NULL
          AND YEAR(lb.updated_at)=%s AND MONTH(lb.updated_at)=%s
        """,
        (prev_date.year, prev_date.month)
    )
    auto_prev = float(cur.fetchone()[0] or 0)

    # Expenses
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (year, month)
    )
    current_expenses = float(cur.fetchone()[0] or 0)

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
        (prev_date.year, prev_date.month)
    )
    prev_expenses = float(cur.fetchone()[0] or 0)

    current_profit = (manual_current + auto_current) - current_expenses
    prev_profit = (manual_prev + auto_prev) - prev_expenses

    percentage_change = 0.0
    if prev_profit != 0:
        percentage_change = ((current_profit - prev_profit) / abs(prev_profit)) * 100
    elif current_profit > 0:
        percentage_change = 100.0

    cur.close()
    conn.close()

    return {
        "amount": current_profit,
        "percentage_change": round(percentage_change, 1)
    }


def get_financial_metrics() -> Dict[str, any]:
    """Get all key financial metrics for the dashboard"""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    return {
        "total_creditors": get_total_unpaid_creditors(),
        "monthly_revenue": get_monthly_revenue_with_comparison(current_year, current_month),
        "net_profit": get_net_profit_with_comparison(current_year, current_month)
    }


def get_six_month_trend() -> List[Dict[str, any]]:
    """Get revenue vs expenses trend for the past 6 months (Jalali month labels)."""
    conn = get_connection(True)
    cur = conn.cursor()

    # Persian month names for labeling
    persian_months = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]
    
    trend_data = []
    now = datetime.now()
    
    def gregorian_to_jalali(gy: int, gm: int, gd: int):
        g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
        gy2 = gy - 1600
        gm2 = gm - 1
        gd2 = gd - 1
        g_day_no = 365*gy2 + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400
        g_day_no += g_d_m[gm2] + gd2
        if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
            g_day_no += 1
        j_day_no = g_day_no - 79
        j_np = j_day_no // 12053
        j_day_no = j_day_no % 12053
        jy = 979 + 33*j_np + 4*(j_day_no//1461)
        j_day_no %= 1461
        if j_day_no >= 366:
            jy += (j_day_no - 366)//365 + 1
            j_day_no = (j_day_no - 366) % 365
        if j_day_no < 186:
            jm = 1 + j_day_no//31
            jd = 1 + (j_day_no % 31)
        else:
            jm = 7 + (j_day_no - 186)//30
            jd = 1 + ((j_day_no - 186) % 30)
        return jy, jm, jd
    
    # Walk back month-by-month reliably
    g_year, g_month = now.year, now.month
    for _ in range(6):  # current and previous 5
        # Label by Jalali month/year from first day of Gregorian month
        jy, jm, _ = gregorian_to_jalali(g_year, g_month, 1)
        month_label = f"{persian_months[jm-1]} {jy}"

        # Manual revenue and expenses (Gregorian month buckets)
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM revenues WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
            (g_year, g_month)
        )
        manual_rev = float(cur.fetchone()[0] or 0)
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE YEAR(created_at)=%s AND MONTH(created_at)=%s",
            (g_year, g_month)
        )
        manual_exp = float(cur.fetchone()[0] or 0)

        # Auto revenue from sold loans in this Gregorian month
        cur.execute(
            """
            SELECT COALESCE(SUM(lb.sale_price - l.purchase_rate), 0)
            FROM loan_buyers lb
            LEFT JOIN loans l ON lb.loan_id = l.id
            WHERE lb.processing_status = 'loan_paid'
              AND lb.sale_price IS NOT NULL AND l.purchase_rate IS NOT NULL
              AND YEAR(lb.updated_at)=%s AND MONTH(lb.updated_at)=%s
            """,
            (g_year, g_month)
        )
        auto_rev = float(cur.fetchone()[0] or 0)

        revenue = manual_rev + auto_rev
        expenses = manual_exp

        trend_data.append({
            "month": month_label,
            "revenue": revenue,
            "expenses": expenses,
            "profit": revenue - expenses
        })

        # Step one month back
        if g_month == 1:
            g_month = 12
            g_year -= 1
        else:
            g_month -= 1

    # Reverse to chronological order (oldest to newest)
    trend_data.reverse()
    
    cur.close()
    conn.close()
    return trend_data


def list_transactions() -> List[Dict[str, any]]:
    """Get all financial transactions (revenues and expenses) sorted by date"""
    conn = get_connection(True)
    cur = conn.cursor()
    
    transactions = []
    
    # Get revenues
    cur.execute(
        "SELECT id, source, amount, created_at FROM revenues ORDER BY created_at DESC"
    )
    revenues = cur.fetchall()
    
    for txn_id, source, amount, created_at in revenues:
        transactions.append({
            "id": txn_id,
            "type": "revenue",
            "description": source,
            "amount": float(amount or 0),
            "date": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else ""
        })
    
    # Get expenses
    cur.execute(
        "SELECT id, source, amount, created_at FROM expenses ORDER BY created_at DESC"
    )
    expenses = cur.fetchall()
    
    for txn_id, source, amount, created_at in expenses:
        transactions.append({
            "id": txn_id,
            "type": "expense",
            "description": source,
            "amount": float(amount or 0),
            "date": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else ""
        })
    
    # Sort by date descending
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    cur.close()
    conn.close()
    return transactions


def delete_transaction(transaction_id: int, transaction_type: str) -> bool:
    """Delete a financial transaction by ID and type"""
    conn = get_connection(True)
    cur = conn.cursor()
    
    table = "revenues" if transaction_type == "revenue" else "expenses"
    
    # Check if transaction exists
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id=%s", (transaction_id,))
    exists = cur.fetchone()[0] > 0
    
    if exists:
        cur.execute(f"DELETE FROM {table} WHERE id=%s", (transaction_id,))
        conn.commit()
    
    cur.close()
    conn.close()
    return exists
