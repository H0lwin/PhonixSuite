# راهنمای راه‌اندازی و پیکربندی PhonixSuite

این راهنما در دو بخش تنظیم شده است:
- بخش 1: نحوه اجرای کد سمت سرور روی سرور لینوکسی (گام‌به‌گام)
- بخش 2: وقتی IP سرور تغییر کرد، چه فایل‌ها و تنظیماتی در کلاینت و سرور باید تغییر کنند

---

## بخش 1 — راه‌اندازی PhonixSuite روی سرور لینوکس

### 1) به‌روز کردن و آماده‌سازی سرور
```bash
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv build-essential
sudo apt autoremove -y
sudo apt autoclean -y
```

### 2) کلون کردن مخزن و رفتن به پوشه سرور
```bash
cd /opt
git clone https://github.com/H0lwin/PhonixSuite.git
cd PhonixSuite/server
```

### 3) ساخت virtual environment و نصب پیش‌نیازها
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
- در صورت نیاز، Gunicorn را جدا نصب کنید:
```bash
pip install gunicorn
```

### 4) ساخت فایل محیطی (.env)
- در مسیر `/opt/PhonixSuite` فایل `.env` بسازید:
```bash
nano /opt/PhonixSuite/.env
```
- محتوا (نمونه):
```
DB_HOST=31.57.26.18
DB_PORT=3306
DB_USER=H0lwin
DB_PASSWORD=Shayan.1400
DB_NAME=phonix
```

### 5) ایجاد کاربر ادمین اپ (CLI تعاملی)
```bash
cd /opt/PhonixSuite
source server/venv/bin/activate
python server/app.py --create-admin --force
```
- این دستور در ترمینالِ تعاملی از شما نام، کدملی (۱۰ رقم) و رمز را می‌پرسد و ادمین می‌سازد.

### 6) اجرای اپ با Gunicorn (موقت برای تست)
```bash
cd /opt/PhonixSuite
source server/venv/bin/activate
gunicorn -w 4 -k gthread -b 0.0.0.0:8000 "server.wsgi:application"
```
- این اجرا موقت است و با بستن ترمینال متوقف می‌شود.

### 7) نصب و آماده‌سازی MySQL
```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql
sudo systemctl status mysql  # بررسی وضعیت
```

### 8) تنظیم دیتابیس و یوزر MySQL
- ورود به MySQL:
```bash
sudo mysql -u root
```
- سپس دستورات زیر را در محیط MySQL اجرا کنید:
```sql
CREATE DATABASE phonix;
CREATE USER 'H0lwin'@'localhost' IDENTIFIED BY 'Shayan.1400';
GRANT ALL PRIVILEGES ON phonix.* TO 'H0lwin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 9) نصب Supervisor
```bash
sudo apt update
sudo apt install supervisor -y
sudo systemctl status supervisor
```

### 10) ساخت فایل کانفیگ Supervisor
- فایل `/etc/supervisor/conf.d/phonix.conf` را بسازید:
```bash
sudo nano /etc/supervisor/conf.d/phonix.conf
```
- محتوا:
```ini
[program:phonix]
directory=/opt/PhonixSuite
command=/opt/PhonixSuite/server/venv/bin/gunicorn -w 4 -k gthread -b 0.0.0.0:8000 server.wsgi:application
autostart=true
autorestart=true
stderr_logfile=/opt/PhonixSuite/logs/phonix.err.log
stdout_logfile=/opt/PhonixSuite/logs/phonix.out.log
environment=PATH="/opt/PhonixSuite/server/venv/bin",PYTHONUNBUFFERED=1
user=root
```
- اگر پوشه لاگ وجود ندارد:
```bash
sudo mkdir -p /opt/PhonixSuite/logs
sudo chown -R root:root /opt/PhonixSuite/logs
```

### 11) فعال‌سازی برنامه در Supervisor
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start phonix
sudo supervisorctl status phonix
```

### 12) مدیریت برنامه با Supervisor
```bash
sudo supervisorctl stop phonix    # توقف برنامه
sudo supervisorctl start phonix   # اجرای مجدد برنامه
sudo supervisorctl restart phonix # ریستارت
sudo supervisorctl status phonix  # بررسی وضعیت
```

### 13) بررسی وضعیت سلامت سرویس
```bash
curl -s http://127.0.0.1:8000/health
# خروجی مورد انتظار: {"status":"ok"}
```

---

## بخش 2 — تغییر IP سرور؛ چه چیزهایی باید تغییر کند؟
وقتی IP یا پورت سرویس API تغییر کرد، لازم است تنظیمات سمت «کلاینت» و گاهی «سرور» به‌روز شوند.

### A) تغییرات لازم در کلاینت (Phoenix.exe یا اجرا از سورس)
- **اولویت تعیین آدرس سرور در کلاینت** بر اساس `client/config.py`:
  1) متغیر محیطی `SERVER_BASE_URL`
  2) فایل `config.json` کنار فایل اجرایی (Phoenix.exe)
  3) فایل `client/config.json` در سورس
  4) پیش‌فرض: `http://127.0.0.1:5000`

- ساده‌ترین راه برای نسخه بسته‌بندی‌شده (Windows):
  - **فایل کنار Phoenix.exe** ایجاد/ویرایش کنید:
    - مسیر: `dist/config.json`
    - محتوا:
    ```json
    {
      "server_base_url": "http://NEW_IP:NEW_PORT"
    }
    ```
  - Phoenix.exe را مجدد اجرا کنید.

- روش با متغیر محیطی موقت (Windows PowerShell):
```powershell
$env:SERVER_BASE_URL = "http://NEW_IP:NEW_PORT"
Start-Process "path\to\Phoenix.exe"
```

- اگر از سورس اجرا می‌کنید (برای توسعه):
  - فایل `client/config.json` را به‌روزرسانی کنید:
    ```json
    {
      "server_base_url": "http://NEW_IP:NEW_PORT"
    }
    ```

- تست اتصال از سیستم کلاینت:
```powershell
curl http://NEW_IP:NEW_PORT/health
```

### B) تغییرات لازم در سرور
- **Binding سرویس API**: در Supervisor یا دستور Gunicorn اگر پورت را عوض کرده‌اید، `-b 0.0.0.0:NEW_PORT` را به‌روزرسانی کنید:
```ini
command=/opt/PhonixSuite/server/venv/bin/gunicorn -w 4 -k gthread -b 0.0.0.0:NEW_PORT server.wsgi:application
```
- **فایروال/Ruleها**: اطمینان از باز بودن پورت جدید در فایروال و امنیت شبکه (UFW/Security Group).
- **DNS/دامنه (اختیاری ولی توصیه‌شده)**: اگر دامنه دارید، A record را به IP جدید اشاره دهید و در کلاینت به جای IP از دامنه استفاده کنید.
- **پیکربندی دیتابیس**: اگر MySQL روی هاست دیگری است و IP دیتابیس تغییر کرده، در فایل `.env` مقدار زیر را به‌روزرسانی کنید:
  - `DB_HOST=NEW_DB_IP`
  - در صورت تغییر پورت/کاربر/رمز، مقادیر `DB_PORT`، `DB_USER`، `DB_PASSWORD` را نیز اصلاح کنید.
- **اعمال تغییرات Supervisor**:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart phonix
```

### C) نکات تکمیلی
- **نقطه سلامت**: همیشه با `/health` آماده‌بودن سرویس را چک کنید.
- **لاگ‌ها**: در سرور، لاگ‌ها در `/opt/PhonixSuite/logs/` ذخیره می‌شوند. خطاها را در `phonix.err.log` بررسی کنید.
- **WSGI پایدار**: برای تولید، همیشه از ورودی WSGI یعنی `server.wsgi:application` استفاده کنید تا فرآیندهای bootstrap (ساخت جداول، لاگ‌ها، توکن‌ها) انجام شوند.
- **ادمین تعاملی**: برای ساخت یا بازسازی ادمین، از دستور CLI تعاملی استفاده کنید:
```bash
cd /opt/PhonixSuite
source server/venv/bin/activate
python server/app.py --create-admin --force
```

---

اگر سوال یا سناریوی خاصی دارید (تغییر پورت، مهاجرت به دامنه، Nginx/HTTPS، یا چندسروره کردن)، اضافه کنیم تا راهنما کامل‌تر شود.

دستور تبدیل کلاینت به exe:
```bash
d:\code\Web\site\sql\app\.venv\Scripts\pyinstaller.exe --noconsole --onefile --name Phoenix --clean --paths d:\code\Web\site\sql\app --collect-all PySide6 --collect-submodules client --add-data "d:\code\Web\site\sql\app\client\config.json;." --add-data "d:\code\Web\site\sql\app\client\assets;assets" d:\code\Web\site\sql\app\client\main.py
```