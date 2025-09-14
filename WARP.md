# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

A Python client–server application for managing Loans, Loan Buyers, Creditors, HR, and Financials with role-based access control and a PySide6 desktop client.

## Tech Stack
- **Backend**: Flask 3, MySQL (mysql-connector-python)
- **Client**: PySide6 (Qt for Python) 
- **HTTP**: requests (centralized API client injects auth headers)
- **Auth**: In-memory token via `X-Auth-Token` header
- **Secrets/Config**: `.env` for DB connection
- **Security**: bcrypt for password hashing

## Architecture

### High-Level Structure
This is a **client-server application** with clear separation:
- **Server** (`server/`): Flask REST API with MySQL database
- **Client** (`client/`): PySide6 desktop application with GUI

### Server Architecture
- **Entry Point**: `server/app.py` - Main Flask app with CLI utilities
- **Database Layer**: `server/database.py` - MySQL connection management
- **Models** (`server/models/`): Database schema and operations for each entity
- **Routes** (`server/routes/`): REST API endpoints organized by feature
- **Services** (`server/services/`): Business logic layer
- **Utils** (`server/utils/`): Authentication and validation utilities

### Client Architecture
- **Entry Point**: `client/main.py` - PySide6 application with Persian UI
- **Views** (`client/views/`): Main application screens/tabs
- **Components** (`client/components/`): Reusable UI components and dialogs
- **Services** (`client/services/`): API client and authentication service
- **State** (`client/state/`): Session management (token, role, user info)
- **Utils** (`client/utils/`): UI styles and internationalization

### Key Architectural Patterns

#### Authentication Flow
1. Client sends login to `POST /api/auth/login` with national_id/password
2. Server validates bcrypt hash, returns JWT-like token
3. Client stores token in session state
4. All subsequent API calls include `X-Auth-Token` header via centralized `api_client.py`

#### Role-Based Access Control (RBAC)
- **Admin**: Full permissions across all modules
- **Secretary**: Read-only access to loan fields  
- **Broker**: Restricted to their own LoanBuyer records
- **Accountant**: Finance and attendance endpoints only

#### Database Design
- MySQL with utf8mb4 encoding
- Auto-schema creation on startup
- Foreign key relationships: loan_buyers→loans, creditor_installments→creditors
- Status tracking with history tables (loan_buyer_status_history)

## Common Development Commands

### Server Operations
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run development server
python server/app.py

# Create admin user (first time setup)
python server/app.py --create-admin

# Force create admin user (overwrite existing)
python server/app.py --create-admin --force

# Migrate plain-text passwords to bcrypt
python server/app.py --migrate-passwords

# Backfill missing creditors for purchased loans
python server/app.py --backfill-creditors

# Update creditor metadata from loan records
python server/app.py --backfill-creditor-metadata
```

### Client Operations
```powershell
# Run desktop client
python client/main.py
```

### Development Setup
```powershell
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
# DB_HOST=127.0.0.1
# DB_PORT=3306  
# DB_USER=your_db_user
# DB_PASSWORD=your_db_password
# DB_NAME=sherkat_app
```

### Code Quality Tools
The environment includes these tools (check with `pip list`):
- **black**: Code formatting
- **flake8**: Linting 
- **mypy**: Type checking
- **pytest**: Testing framework

```powershell
# Format code
black server/ client/

# Lint code  
flake8 server/ client/

# Type checking
mypy server/ client/

# Run tests
pytest
```

## Database Schema Key Points

### Core Entities
- **employees**: User accounts with roles (admin/secretary/broker/accountant)
- **loans**: Core loan records with owner info and purchase rates
- **loan_buyers**: People buying loans, linked to loans and brokers
- **creditors**: Auto-created when loans become "purchased"
- **creditor_installments**: Payment tracking with auto-settlement
- **revenues/expenses**: Financial tracking

### Important Relationships
- Loan Buyers reference Loans (`loan_buyers.loan_id → loans.id`)
- Creditors auto-created from purchased Loans with metadata
- Status changes tracked in history tables
- Branch/Department hierarchies for employee organization

## API Patterns

### Authentication Endpoints
- `POST /api/auth/login` - Returns role, display_name, token
- `POST /api/auth/logout` - Revokes token

### CRUD Patterns
Most entities follow RESTful patterns:
- `GET /api/{entity}` - List (with role-based filtering)
- `GET /api/{entity}/<id>` - Detail 
- `POST /api/{entity}` - Create
- `PATCH /api/{entity}/<id>` - Update
- `DELETE /api/{entity}/<id>` - Delete (admin only)

### Specialized Endpoints  
- `GET /api/employees/meta` - Departments/branches for dropdowns
- `POST /api/creditors/<id>/installments` - Add payment with auto-settle
- `GET /api/finance/summary/<year>/<month>` - Monthly financial reports

## Client UI Architecture

### Persian RTL Interface
- All UI text in Persian/Farsi
- Right-to-left layout direction
- Vazir font family when available

### Main Components
- **Login Window** (`پنجره_ورود`): National ID + password authentication
- **Dashboard** (`پنجره_داشبورد`): Main app window with sidebar navigation
- **Navigation Tree**: Hierarchical menu with role-based items
- **Stacked Content**: Pages switch based on sidebar selection

### Dialog System
- **View Dialogs**: Read-only popups for record details
- **Edit Dialogs**: Form-based editing with validation
- **Add Dialogs**: New record creation forms
- Consistent styling with light theme

## Development Workflow Considerations

### Environment Setup
1. Ensure MySQL server running with utf8mb4 support
2. Create database (auto-created by app if missing)
3. Configure `.env` with database credentials
4. Install Python dependencies from `requirements.txt`
5. Create initial admin user with `--create-admin`

### Adding New Features
1. **Server-side**: Add model in `models/`, route in `routes/`, service in `services/`
2. **Client-side**: Create view in `views/`, dialogs in `components/`
3. Update navigation in `client/main.py` dashboard
4. Add API client methods in `client/services/api_client.py`

### Database Changes
- Schema changes handled in model `ensure_*_schema()` functions
- Use migration utilities in `server/app.py` for data transformations
- Always test with existing data to ensure backward compatibility

### Authentication Integration
- All API calls must use `client/services/api_client.py` for token injection
- Role-based UI hiding handled in dashboard navigation setup
- Server-side authorization enforced in route decorators

## Important Implementation Notes

### Security Considerations  
- Passwords stored as bcrypt hashes (migration helper available)
- Tokens stored in memory (prototype - consider DB/JWT for production)
- Environment variables for sensitive configuration
- SQL injection prevention through parameterized queries

### Logging System
- Server logs to `logs/server.log` with rotation
- Client logs to `logs/client.log` with rotation  
- Structured logging with timestamps and levels

### Error Handling
- Global Flask error handler returns JSON responses
- Client uses consistent error display patterns
- Network timeouts and connection errors handled gracefully

### Performance Considerations
- Database connections use autocommit for consistency
- Client-side filtering for small datasets (employees, branches)
- Pagination should be implemented for large datasets
- Consider connection pooling for production deployment