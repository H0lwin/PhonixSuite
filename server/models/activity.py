# -*- coding: utf-8 -*-
"""Activity logging model.
- Persistent storage of user actions with status and details
- Query with filters (by user, date range)
- Auto-cleanup rows older than 30 days
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from database import get_connection


def ensure_activity_schema():
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NULL,
            user_name VARCHAR(191) NULL,
            action VARCHAR(191) NOT NULL,
            details TEXT NULL,
            status ENUM('success','failure','error') NOT NULL DEFAULT 'success',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_created_at (created_at),
            KEY idx_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
    )
    conn.commit(); cur.close(); conn.close()


def cleanup_old_logs():
    """Delete logs older than 30 days."""
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute("DELETE FROM activity_logs WHERE created_at < (NOW() - INTERVAL 30 DAY)")
    conn.commit(); cur.close(); conn.close()


def add_log(user_id: Optional[int], user_name: Optional[str], action: str, details: Optional[str], status: str = "success") -> int:
    conn = get_connection(True)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO activity_logs (user_id, user_name, action, details, status)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (user_id, user_name, action[:191], details, status),
    )
    new_id = cur.lastrowid
    # Auto cleanup opportunistically
    try:
        cur2 = conn.cursor(); cur2.execute("DELETE FROM activity_logs WHERE created_at < (NOW() - INTERVAL 30 DAY)"); cur2.close()
    except Exception:
        pass
    conn.commit(); cur.close(); conn.close()
    return new_id


def list_logs(user_id: Optional[int] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, limit: int = 500) -> List[Dict[str, Any]]:
    conn = get_connection(True)
    cur = conn.cursor()
    sql = [
        """
        SELECT id, created_at, user_name, action, details, status
        FROM activity_logs
        """
    ]
    where = []
    params: List[Any] = []
    if user_id:
        where.append("user_id=%s"); params.append(user_id)
    if date_from:
        where.append("created_at >= %s"); params.append(datetime.combine(date_from, datetime.min.time()))
    if date_to:
        where.append("created_at <= %s"); params.append(datetime.combine(date_to, datetime.max.time()))
    if where:
        sql.append("WHERE "+ " AND ".join(where))
    sql.append("ORDER BY created_at DESC")
    sql.append("LIMIT %s"); params.append(limit)
    q = "\n".join(sql)
    cur.execute(q, tuple(params))
    rows = cur.fetchall(); cur.close(); conn.close()
    cols = ["id","created_at","user_name","action","details","status"]
    return [dict(zip(cols, r)) for r in rows]


def list_recent(limit: int = 10) -> List[Dict[str, Any]]:
    return list_logs(limit=limit)