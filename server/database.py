# -*- coding: utf-8 -*-
import os
import mysql.connector


def get_connection(database: bool = True):
    """Create a MySQL connection. If database=False, connects without selecting a DB.
    Ensures UTF-8 settings after connect.
    """
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "1234")
    dbname = os.getenv("DB_NAME", "myapp")

    kwargs = dict(host=host, port=port, user=user, password=password, autocommit=True)
    if database:
        kwargs["database"] = dbname

    conn = mysql.connector.connect(**kwargs)
    try:
        cur = conn.cursor()
        # Ensure proper charset/collation after connect
        cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_general_ci")
        cur.close()
    except Exception:
        pass
    return conn