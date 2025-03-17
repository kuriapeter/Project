from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import current_app

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, finance, employee
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', back_populates='employees')
    
    def set_password(self, password):
        """Set user password with complexity validation."""
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")
        
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")
        if not any(not c.isalnum() for c in password):
            raise ValueError("Password must contain at least one special character")
        
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'
    
    def is_finance(self):
        return self.role == 'finance'
    
    def can_view_department(self, department_id):
        if self.is_admin() or self.is_finance():
            return True
        return self.department_id == department_id

    def has_role(self, *roles):
        return self.role in roles

    def can_manage_transactions(self):
        """Check if user can manage transactions."""
        return self.role in ['admin', 'finance']

    def can_view_transactions(self):
        """Check if user can view transactions."""
        return True  # All users can view transactions

    def can_edit_transactions(self):
        """Check if user can edit transactions."""
        return self.role in ['admin', 'finance']

    def can_approve_transactions(self):
        """Check if user can approve transactions."""
        return self.role in ['admin', 'finance']

    def can_view_budgets(self):
        """Check if user can view budgets."""
        return self.role in ['admin', 'finance']

    def can_edit_budgets(self):
        """Check if user can edit budgets."""
        return self.role in ['admin', 'finance']

    def can_view_reports(self):
        """Check if user can view reports."""
        return True  # All users can view reports

    def can_view_payroll(self):
        """Check if user can view payroll information."""
        return self.role in ['admin', 'finance', 'hr']

    def can_manage_payroll(self):
        """Check if user can manage payroll."""
        return self.role in ['admin', 'finance']

    def can_approve_payroll(self):
        """Check if user can approve payroll."""
        return self.role in ['admin', 'finance']

    def can_edit_payroll(self):
        """Check if user can edit payroll records."""
        return self.role in ['admin', 'finance']

    def can_process_payroll(self):
        """Check if user can process payroll payments."""
        return self.role in ['admin', 'finance']

    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    budget_limit = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employees = db.relationship('User', back_populates='department')
    transactions = db.relationship('Transaction', back_populates='department')
    
    def get_monthly_expenses(self, year=None, month=None):
        if year is None or month is None:
            now = datetime.utcnow()
            year = now.year
            month = now.month
            
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
            
        total = sum(t.amount for t in self.transactions 
                   if t.type == 'expense' 
                   and start_date <= t.date < end_date)
        return total
    
    def get_monthly_income(self, year=None, month=None):
        if year is None or month is None:
            now = datetime.utcnow()
            year = now.year
            month = now.month
            
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
            
        total = sum(t.amount for t in self.transactions 
                   if t.type == 'income' 
                   and start_date <= t.date < end_date)
        return total

    def __repr__(self):
        return f'<Department {self.name}>'

class Budget(db.Model):
    __tablename__ = 'budgets'
    category = db.Column(db.String(50), primary_key=True)
    budget_amount = db.Column(db.Float, nullable=False)
    
    # Relationships
    transactions = db.relationship('Transaction', back_populates='budget')
    
    def __init__(self, category, budget_amount):
        self.category = category
        self.budget_amount = budget_amount
    
    def to_dict(self):
        return {
            'category': self.category,
            'budget_amount': self.budget_amount
        }
    
    def __repr__(self):
        return f'<Budget {self.category}: {self.budget_amount}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # income/expense
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), db.ForeignKey('budgets.category'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    approval_date = db.Column(db.DateTime)
    
    # Relationships
    budget = db.relationship('Budget', back_populates='transactions')
    department = db.relationship('Department', back_populates='transactions')
    creator = db.relationship('User', foreign_keys=[creator_id])
    approver = db.relationship('User', foreign_keys=[approver_id])
    
    def __init__(self, type, amount, description, category, department_id, creator_id, date=None, status='pending'):
        self.type = type
        self.amount = amount
        self.description = description
        self.category = category
        self.department_id = department_id
        self.creator_id = creator_id
        self.date = date if date else datetime.utcnow()
        self.status = status
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'amount': self.amount,
            'description': self.description,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S'),
            'category': self.category,
            'status': self.status,
            'creator': self.creator.username,
            'approver': self.approver.username if self.approver else None,
            'department': self.department.name,
            'approval_date': self.approval_date.strftime('%Y-%m-%d %H:%M:%S') if self.approval_date else None
        }
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.type} {self.amount}>'

class Payroll(db.Model):
    __tablename__ = 'payroll'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    salary_amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('User', foreign_keys=[employee_id])
    
    def __init__(self, employee_id, salary_amount, payment_date):
        self.employee_id = employee_id
        self.salary_amount = salary_amount
        self.payment_date = payment_date
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee': self.employee.username,
            'salary_amount': self.salary_amount,
            'payment_date': self.payment_date.strftime('%Y-%m-%d'),
            'status': self.status,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<Payroll {self.id}: {self.employee.username} {self.salary_amount}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # login, logout, create, update, delete
    resource_type = db.Column(db.String(50), nullable=False)  # user, transaction, budget, etc.
    resource_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __init__(self, user_id, action, resource_type, resource_id=None, details=None, ip_address=None):
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.ip_address = ip_address
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.username,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.action} on {self.resource_type}>'
