# Company Finance Tracker

A Flask-based financial management system for tracking company finances, managing budgets, and handling payroll.

## Features

- Transaction management (income/expenses)
- Budget tracking and management
- Financial analytics and reporting
- Payroll system
- User authentication and role-based access

## Technical Stack

- Backend: Flask + MySQL
- Authentication: Flask-Login
- Database: SQLAlchemy ORM
- Frontend: Templates with charts/visualization

## Setup Instructions

1. Install XAMPP and ensure MySQL service is running
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create the database:
   ```bash
   mysql -u root -e "CREATE DATABASE company_finance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```

4. Initialize the database:
   ```bash
   flask db upgrade
   ```

5. Run the application:
   ```bash
   flask run
   ```

## Default Admin Credentials

- Username: admin
- Password: Admin@123
- Email: admin@company.com

## Production Deployment

For production deployment:

1. Set required environment variables:
   - SECRET_KEY
   - WTF_CSRF_SECRET_KEY
   - DATABASE_URL
   - FLASK_ENV=production

2. Use a production WSGI server (e.g., Waitress):
   ```bash
   python wsgi.py
   ```

3. Configure your web server (e.g., Nginx) to proxy requests to the application

## Security Features

- Password hashing using Werkzeug
- Role-based access control
- Session management
- CSRF protection
- Rate limiting
- Audit logging

## Database Structure

1. Users:
   - id (Primary Key)
   - name
   - email (Unique)
   - username (Unique)
   - password_hash
   - role

2. Transactions:
   - type (income/expense)
   - amount
   - description
   - date
   - category
   - status

3. Budgets:
   - category (Primary Key)
   - budget_amount

4. Payroll:
   - id (Primary Key)
   - employee_id
   - salary_amount
   - pay_date
   - status
   - notes
