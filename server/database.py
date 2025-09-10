# -*- coding: utf-8 -*-
import os
import mysql.connector


def get_connection(database: bool = True):
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "1234")
    dbname = os.getenv("DB_NAME", "myapp")

    kwargs = dict(host=host, port=port, user=user, password=password, charset="utf8mb4", collation="utf8mb4_general_ci", autocommit=True)
    if database:
        kwargs["database"] = dbname
    return mysql.connector.connect(**kwargs)


