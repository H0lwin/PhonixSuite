# Project Overview
A Python client–server application for managing Loans, Loan Buyers, Creditors, HR, and Financials with role-based access control and a PySide6 desktop client.

## Tech Stack
- **Backend**: Flask 3, MySQL (mysql-connector-python)
- **Client**: PySide6 (Qt for Python)
- **HTTP**: requests (centralized API client injects auth headers)
- **Auth**: In-memory token via `X-Auth-Token` header
- **Secrets/Config**: `.env` for DB connection (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- **Security**: bcrypt for password hashing

## Modules & Entities
### HR (Employees & Attendance)
- **Employee** fields: `id, full_name, national_id, password (bcrypt), role, department_id, branch_id, phone, address, monthly_salary, status`
- **Attendance**: `employee_id, date, check_in, check_out, status, notes`

### Loan Management
- **Loan** fields: `bank_name, loan_type, duration, amount, owner_full_name, owner_phone, visit_date, loan_status, introducer, payment_type, purchase_rate`

### Loan Buyers
- **LoanBuyer** fields: `first_name, last_name, national_id, phone, requested_amount, bank_agent, visit_date, processing_status, notes, loan_id, broker, sale_price, sale_type`
- **Status History**: Tracks status changes with timestamps

### Creditors & Installments
- Auto-created when a Loan’s status becomes "purchased"
- **Creditor**: `full_name, amount, description, settlement_status`
- **Installments**: `{amount, date, notes}` with auto-settle when fully paid

### Finance
- Revenues and Expenses with monthly summary endpoint

## Access Control (RBAC)
- **Admin**: full permissions
- **Secretary**: read-only fields in Loan module
- **Broker**: restricted to their own LoanBuyer records (read/update limited to ownership)
- **Accountant**: finance and attendance endpoints

## Backend Endpoints (highlights)
### Auth
- `POST /api/auth/login` → `{status, role, display_name, token}` (verifies bcrypt hash; supports legacy fallback)
- `POST /api/auth/logout` → revokes token (in-memory)
- Header: `X-Auth-Token: <token>`

### Employees
- `GET /api/employees/meta` (admin) → departments, branches
- `GET /api/employees` (admin) → list
- `POST /api/employees` (admin) → create (hashes password)
- `GET /api/employees/<id>` (admin) → detail
- `PATCH /api/employees/<id>` (admin) → update (hash password if provided)
- `DELETE /api/employees/<id>` (admin) → delete

### Attendance
- `POST /api/attendance` (admin, accountant)
- `GET /api/attendance/<employee_id>` (admin, accountant)

### Loans
- `GET /api/loans` (auth)
- `GET /api/loans/<id>` (auth)
- `POST /api/loans` (admin)
- `PATCH /api/loans/<id>` (admin)

### Loan Buyers
- `GET /api/loan-buyers` (auth): admin sees all; broker sees only their own
- `POST /api/loan-buyers` (admin, broker): broker auto-sets `broker`
- `PATCH /api/loan-buyers/<id>` (admin, broker): ownership restricted (broker)

### Creditors
- `GET /api/creditors` (admin)
- `POST /api/creditors/<id>/installments` (admin): add installment; auto-settle on full payment

### Finance
- `POST /api/finance/revenue` (admin, accountant)
- `POST /api/finance/expense` (admin, accountant)
- `GET /api/finance/summary/<year>/<month>` (admin, accountant)

## Database Schema (summary)
Tables: `employees, departments, branches, attendance, loans, loan_buyers, loan_buyer_status_history, creditors, creditor_installments, revenues, expenses`
- Relations:
  - `loan_buyers.loan_id → loans.id`
  - `loan_buyer_status_history.loan_buyer_id → loan_buyers.id`
  - `creditor_installments.creditor_id → creditors.id`

## Client (PySide6) Overview
- **Login Window**: collects national_id/password; on success opens dashboard with token; logout revokes token
- **Dashboard Layout**: right sidebar navigation + left content stack; fullscreen; light theme
- **User Management (Admin)**:
  - Employees table with actions: View (read-only popup), Edit (editable popup), Delete (confirm then delete)
  - "Add Employee" button opens a popup with all required fields; on submit, table refreshes
- **API Client**: centralized module adds `X-Auth-Token` to all requests

## Security Notes
- Passwords stored as bcrypt hashes
- Migration helper available to hash existing plain-text passwords
- Tokens stored in memory (prototype); consider DB/JWT for production
- `.env` is git-ignored; rotate DB password if leaked

## How to Run
Backend:
1. Activate venv
2. Run server:
   - `python "d:\code\Web\site\sql\app - Copy\server\app.py"`
3. Create admin if none:
   - `python "d:\code\Web\site\sql\app - Copy\server\app.py" --create-admin --force`
4. Migrate existing passwords to bcrypt:
   - `python "d:\code\Web\site\sql\app - Copy\server\app.py" --migrate-passwords`

Client:
- `python "d:\code\Web\site\sql\app - Copy\client\main.py"`

## UI/UX
- Light theme; white background, dark text
- Right sidebar navigation; stacked content pages
- Modernized user management table and dialogs

## Next Steps / Ideas
- Persist tokens (DB) or switch to short-lived JWTs
- Field-level ACL in client for secretary view
- Payroll calculation from attendance + base salary; monthly expenses posting
- Add sidebar sections for Loans, Loan Buyers, Creditors, and Finance with consistent dialogs/tables