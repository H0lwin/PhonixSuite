# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import os
import getpass
import argparse
import logging
from logging.handlers import RotatingFileHandler
import mysql.connector
from mysql.connector import errorcode


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "1234"),
        "database": os.getenv("DB_NAME", "myapp"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }


def connect_without_db():
    تنظیمات = get_db_config()
    return mysql.connector.connect(
        host=تنظیمات["host"],
        user=تنظیمات["user"],
        password=تنظیمات["password"],
        port=تنظیمات["port"],
        charset="utf8mb4",
        collation="utf8mb4_general_ci",
        autocommit=True,
    )


def connect_to_db():
    تنظیمات = get_db_config()
    return mysql.connector.connect(
        host=تنظیمات["host"],
        user=تنظیمات["user"],
        password=تنظیمات["password"],
        database=تنظیمات["database"],
        port=تنظیمات["port"],
        charset="utf8mb4",
        collation="utf8mb4_general_ci",
        autocommit=True,
    )


def ensure_database_and_tables():
    تنظیمات = get_db_config()
    نام_پایگاه = تنظیمات["database"]

    # 1) بررسی و ایجاد پایگاه داده در صورت عدم وجود
    try:
        اتصال_بدون = connect_without_db()
        با_انجام = اتصال_بدون.cursor()
        با_انجام.execute(
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
            (نام_پایگاه,),
        )
        نتیجه = با_انجام.fetchone()
        if not نتیجه:
            با_انجام.execute(
                f"CREATE DATABASE `{نام_پایگاه}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
            )
            app.logger.info("Database created: %s", نام_پایگاه)
        با_انجام.close()
        اتصال_بدون.close()
    except mysql.connector.Error as خطا:
        app.logger.exception("Database create/check error: %s", خطا)
        raise

    # 2) بررسی و ایجاد جدول ها به صورت جداگانه
    try:
        اتصال = connect_to_db()
        با_انجام = اتصال.cursor()

        # جدول users
        با_انجام.execute(
            """
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
            """,
            (نام_پایگاه, "users"),
        )
        وجود_جدول_کاربران = با_انجام.fetchone()[0] > 0
        if not وجود_جدول_کاربران:
            با_انجام.execute(
                """
                CREATE TABLE `users` (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    `نام_کاربری` VARCHAR(191) UNIQUE NOT NULL,
                    `رمز_عبور` VARCHAR(255) NOT NULL,
                    `نقش` ENUM('admin','user') NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
                """
            )
            app.logger.info("Table created: users")

        با_انجام.close()
        اتصال.close()
    except mysql.connector.Error as خطا:
        app.logger.exception("Tables create/check error: %s", خطا)
        raise


def ensure_admin_wizard(force: bool = False):
    """اگر هیچ ادمینی وجود ندارد، از کاربر بخواه ادمین بسازد. اگر اجباری=True باشد،
    بدون توجه به وجود ادمین، از کاربر می‌خواهد ادمین بسازد (در صورت تکراری بودن نام، خطا می‌دهد و دوباره می‌پرسد)."""
    try:
        اتصال = connect_to_db()
        با_انجام = اتصال.cursor()

        با_انجام.execute("SELECT COUNT(*) FROM users WHERE `نقش`='admin'")
        تعداد_ادمین = با_انجام.fetchone()[0]

        نیاز_به_ادمین = force or (تعداد_ادمین == 0)
        if not نیاز_به_ادمین:
            با_انجام.close()
            اتصال.close()
            return

        print("There is no admin user. Please create an admin user.")
        while True:
            نام = input("Administrator Username: ").strip()
            if not نام:
                print("Username cannot be empty.")
                continue

            # بررسی یکتایی نام کاربری
            با_انجام.execute("SELECT COUNT(*) FROM users WHERE `نام_کاربری`=%s", (نام,))
            اگر_وجود_نام = با_انجام.fetchone()[0] > 0
            if اگر_وجود_نام:
                print("This username already exists. Please choose another one.")
                continue

            گذرواژه = getpass.getpass("Password: ").strip()
            تکرار = getpass.getpass("Repeat password: ").strip()
            if not گذرواژه:
                print("Password cannot be empty.")
                continue
            if گذرواژه != تکرار:
                print("The password and its repetition are not the same.")
                continue

            با_انجام.execute(
                "INSERT INTO users (`نام_کاربری`, `رمز_عبور`, `نقش`) VALUES (%s,%s,%s)",
                (نام, گذرواژه, "admin"),
            )
            اتصال.commit()
            app.logger.info("Admin user created: %s", نام)
            print("Administrator user created successfully.")
            break

        با_انجام.close()
        اتصال.close()
    except mysql.connector.Error as خطا:
        app.logger.exception("Database error creating admin user: %s", خطا)
        raise


@app.route("/login", methods=["POST"])
def login():
    داده = request.get_json(silent=True, force=True)
    if not داده:
        return (
            jsonify({"وضعیت": "خطا", "پیام": "داده‌های ارسالی نامعتبر است."}),
            400,
        )

    نام_کاربری = داده.get("نام_کاربری", "").strip()
    رمز_عبور = داده.get("رمز_عبور", "").strip()

    if not نام_کاربری or not رمز_عبور:
        return (
            jsonify({"وضعیت": "خطا", "پیام": "نام کاربری و رمز عبور الزامی است."}),
            400,
        )

    try:
        اتصال = connect_to_db()
        با_انجام = اتصال.cursor()
        با_انجام.execute(
            "SELECT `نقش` FROM users WHERE `نام_کاربری`=%s AND `رمز_عبور`=%s LIMIT 1",
            (نام_کاربری, رمز_عبور),
        )
        نتیجه = با_انجام.fetchone()
        با_انجام.close()
        اتصال.close()
    except mysql.connector.Error as خطا:
        app.logger.exception("Database error in /login: %s", خطا)
        return (
            jsonify({"وضعیت": "خطا", "پیام": "خطا در ارتباط با پایگاه داده."}),
            500,
        )

    if not نتیجه:
        return (
            jsonify({"وضعیت": "خطا", "پیام": "نام کاربری یا رمز عبور نادرست است."}),
            401,
        )

    نقش_سیستم = نتیجه[0]
    نقش_نمایشی = {"admin": "مدیر", "user": "کاربر"}.get(نقش_سیستم, "کاربر")
    return jsonify({"وضعیت": "موفق", "نقش": نقش_نمایشی})


def start_server():
    ensure_database_and_tables()
    ensure_admin_wizard()


def run_create_admin(force: bool = False):
    ensure_database_and_tables()
    ensure_admin_wizard(force=force)


def configure_logging():
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "server.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    werk = logging.getLogger("werkzeug")
    werk.setLevel(logging.INFO)
    werk.addHandler(handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="اجرای سرور و ابزارهای مدیریتی")
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="اجرای جادوگر ساخت کاربر مدیر (در صورت نبود ادمین آن را می‌سازد)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="همیشه جادوگر ساخت مدیر را اجرا کن، حتی اگر ادمین وجود دارد",
    )
    args = parser.parse_args()

    if args.create_admin:
        configure_logging()
        run_create_admin(force=args.force)
    else:
        configure_logging()
        start_server()
        app.run(host="127.0.0.1", port=5000, debug=True)


