from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Transaction, Budget, AuditLog, db, Department, Payroll
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, TextAreaField, DateField, validators
from forms import LoginForm, TransactionForm, UserRegistrationForm, UserEditForm, ResetPasswordRequestForm, ResetPasswordForm
from utils import validate_password, admin_required, hr_required, finance_required, roles_required
from extensions import limiter
import json
from urllib.parse import urlparse
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view with overview of finances"""
    # Get KPI metrics
    kpis = {
        'total_income': 0.0,
        'total_expenses': 0.0,
        'net_balance': 0.0,
        'income_trend': 0.0,
        'expense_trend': 0.0
    }
    
    # Calculate KPIs
    current_month = datetime.now().replace(day=1)
    transactions = Transaction.query.filter(Transaction.date >= current_month).all()
    
    for transaction in transactions:
        if transaction.type == 'income':
            kpis['total_income'] += transaction.amount
        else:
            kpis['total_expenses'] += transaction.amount
    
    kpis['net_balance'] = kpis['total_income'] - kpis['total_expenses']
    
    # Get trend data (comparing to last month)
    last_month = current_month.replace(month=current_month.month-1 if current_month.month > 1 else 12)
    last_month_transactions = Transaction.query.filter(
        Transaction.date >= last_month,
        Transaction.date < current_month
    ).all()
    
    last_month_income = sum(t.amount for t in last_month_transactions if t.type == 'income')
    last_month_expenses = sum(t.amount for t in last_month_transactions if t.type == 'expense')
    
    # Calculate trends (percentage change)
    if last_month_income > 0:
        kpis['income_trend'] = ((kpis['total_income'] - last_month_income) / last_month_income * 100)
    if last_month_expenses > 0:
        kpis['expense_trend'] = ((kpis['total_expenses'] - last_month_expenses) / last_month_expenses * 100)
    
    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
    
    # Get pending approvals
    pending_approvals = []
    if current_user.role in ['admin', 'manager']:
        pending_approvals = Transaction.query.filter_by(status='pending').all()
    
    # Get upcoming payroll
    upcoming_payroll = []
    if current_user.role in ['admin', 'hr', 'manager']:
        upcoming_payroll = Payroll.query.filter(
            Payroll.payment_date > datetime.now(),
            Payroll.status == 'pending'
        ).order_by(Payroll.payment_date).limit(5).all()
    
    return render_template('dashboard.html',
                         kpis=kpis,
                         recent_transactions=recent_transactions,
                         pending_approvals=pending_approvals,
                         upcoming_payroll=upcoming_payroll)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limiting for brute force protection
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                # Check if user is active
                if not user.is_active:
                    flash('Your account is inactive. Please contact your administrator.', 'error')
                    return render_template('auth/login.html', form=form)
                
                login_user(user, remember=form.remember_me.data)
                
                # Initialize user preferences in session
                session['language'] = session.get('language', 'en')
                session['theme'] = session.get('theme', 'light')
                session['notifications_enabled'] = session.get('notifications_enabled', True)
                
                # Log successful login
                audit_log = AuditLog(
                    user_id=user.id,
                    action='LOGIN_SUCCESS',
                    endpoint='auth.login',
                    ip_address=request.remote_addr,
                    timestamp=datetime.utcnow(),
                    details=json.dumps({
                        'username': user.username,
                        'role': user.role,
                        'remember_me': form.remember_me.data
                    }),
                    resource_type='login',
                    resource_id=None
                )
                db.session.add(audit_log)
                db.session.commit()

                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('auth.dashboard')
                return redirect(next_page)
            else:
                # Log failed login attempt
                if user:
                    audit_log = AuditLog(
                        user_id=user.id,
                        action='LOGIN_FAILED',
                        endpoint='auth.login',
                        ip_address=request.remote_addr,
                        timestamp=datetime.utcnow(),
                        details=json.dumps({
                            'reason': 'Invalid password',
                            'username': user.username
                        }),
                        resource_type='login',
                        resource_id=None
                    )
                else:
                    audit_log = AuditLog(
                        user_id=None,
                        action='LOGIN_FAILED',
                        endpoint='auth.login',
                        ip_address=request.remote_addr,
                        timestamp=datetime.utcnow(),
                        details=json.dumps({
                            'reason': 'User not found',
                            'attempted_username': form.username.data
                        }),
                        resource_type='login',
                        resource_id=None
                    )
                db.session.add(audit_log)
                db.session.commit()
                
                flash('Invalid username or password', 'error')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    # Clear user preferences from session
    session.pop('language', None)
    session.pop('theme', None)
    session.pop('notifications_enabled', None)
    
    # Log logout
    audit_log = AuditLog(
        user_id=current_user.id,
        action='LOGOUT',
        endpoint='auth.logout',
        ip_address=request.remote_addr,
        timestamp=datetime.utcnow(),
        details=json.dumps({
            'username': current_user.username
        }),
        resource_type='logout',
        resource_id=None
    )
    db.session.add(audit_log)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    form = UserRegistrationForm()
    try:
        # Create admin user if no users exist
        if User.query.count() == 0:
            admin = User(
                name='Admin User',
                email='admin@company.com',
                username='admin',
                role='admin'
            )
            admin.set_password('Admin@123')  # Secure default password
            db.session.add(admin)
            
            # Create finance user
            finance = User(
                name='Finance Manager',
                email='finance@company.com',
                username='finance',
                role='finance'
            )
            finance.set_password('Finance@123')  # Secure default password
            db.session.add(finance)
            
            db.session.commit()
            
            # Log user creation
            audit_log = AuditLog(
                user_id=admin.id,
                action='USER_CREATED',
                resource_type='user',
                resource_id=str(admin.id),
                details=json.dumps({
                    'created_users': ['admin', 'finance'],
                    'created_by': 'system'
                }),
                ip_address=request.remote_addr
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('Default admin and finance users created successfully.', 'success')
            return redirect(url_for('auth.login'))
        
        if form.validate_on_submit():
            # Create new user
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                name=form.name.data,
                role=form.role.data,
                department=form.department.data,
                position=form.position.data
            )
            new_user.set_password(form.password.data)

            # Add to database
            db.session.add(new_user)

            # Log user creation
            audit_log = AuditLog(
                user_id=current_user.id,
                action='USER_CREATED',
                endpoint='auth.register',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'created_username': new_user.username,
                    'created_role': new_user.role,
                    'created_by': current_user.username
                }),
                resource_type='users',
                resource_id=str(new_user.id)
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('User created successfully!', 'success')
            return redirect(url_for('auth.user_list'))

    except Exception as e:
        db.session.rollback()
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_CREATION_ERROR',
            endpoint='auth.register',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'attempted_username': form.username.data if form.username.data else None,
                'created_by': current_user.username
            }),
            resource_type='users',
            resource_id=None
        )
        db.session.add(error_log)
        db.session.commit()
        
        print(f"Error in register route: {str(e)}")
        flash('Error creating user. Please try again.', 'error')
        return redirect(url_for('auth.register'))

    return render_template('admin/add_user.html', form=form)

@auth_bp.route('/add-transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # Check user permission
    if not current_user.can_manage_transactions():
        flash('You do not have permission to add transactions.', 'error')
        return redirect(url_for('auth.dashboard'))

    try:
        # Get all budget categories for the form
        categories = [(budget.category, budget.category) for budget in Budget.query.all()]
        
        # Add default budget categories if none exist
        default_categories = ['Housing', 'Transportation', 'Food', 'Entertainment', 'Miscellaneous']
        for category in default_categories:
            if category not in [c[0] for c in categories]:
                new_budget = Budget(category=category, budget_amount=0)
                db.session.add(new_budget)
                db.session.commit()
                categories.append((category, category))
        
        form = TransactionForm()
        form.category.choices = [('', 'Select Category')] + categories

        if request.method == 'POST':
            # Print form data for debugging
            print(f"Form data: type={form.type.data}, amount={form.amount.data}, category={form.category.data}, date={form.date.data}")
            
            if form.validate_on_submit():
                # Create new transaction
                transaction = Transaction(
                    type=form.type.data,
                    amount=float(form.amount.data),
                    category=form.category.data,
                    description=form.description.data or '',  # Handle None description
                    date=form.date.data,
                    user_id=current_user.id,
                    status='pending'  # Default status for new transactions
                )
                
                # Print transaction object for debugging
                print(f"Transaction object: {transaction.to_dict()}")
                
                db.session.add(transaction)
                
                # Update budget tracking
                budget = Budget.query.filter_by(category=transaction.category).first()
                if budget:
                    if transaction.type == 'expense':
                        if transaction.amount > budget.budget_amount:
                            flash(f'Warning: This expense exceeds the budget for {budget.category}', 'warning')
                
                # Log transaction creation
                audit_log = AuditLog(
                    user_id=current_user.id,
                    action='TRANSACTION_CREATED',
                    endpoint='auth.add_transaction',
                    ip_address=request.remote_addr,
                    timestamp=datetime.utcnow(),
                    details=json.dumps({
                        'transaction_type': transaction.type,
                        'amount': float(transaction.amount),
                        'category': transaction.category,
                        'created_by': current_user.username,
                        'date': transaction.date.strftime('%Y-%m-%d')
                    }),
                    resource_type='transaction',
                    resource_id=None
                )
                db.session.add(audit_log)
                
                try:
                    db.session.commit()
                    flash('Transaction added successfully!', 'success')
                    return redirect(url_for('auth.transactions'))
                except Exception as e:
                    db.session.rollback()
                    print(f"Database error: {str(e)}")
                    flash('Database error. Please try again.', 'error')
            else:
                print(f"Form validation errors: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{field.title()}: {error}', 'error')

    except Exception as e:
        db.session.rollback()
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='TRANSACTION_CREATION_ERROR',
            endpoint='auth.add_transaction',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'created_by': current_user.username
            }),
            resource_type='transaction',
            resource_id=None
        )
        db.session.add(error_log)
        db.session.commit()
        
        print(f"Error adding transaction: {str(e)}")
        
        flash('Error adding transaction. Please try again.', 'error')
        return redirect(url_for('auth.add_transaction'))

    return render_template('auth/add_transaction.html', form=form, categories=categories)

@auth_bp.route('/api/dashboard-data')
@login_required
def get_dashboard_data():
    try:
        time_range = request.args.get('timeRange', 'month')
        
        # Calculate date range
        end_date = datetime.utcnow()
        if time_range == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif time_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif time_range == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:  # year
            start_date = end_date - timedelta(days=365)

        # Get transactions for the period
        transactions = Transaction.query.filter(
            Transaction.date.between(start_date, end_date)
        ).all()

        # Calculate totals
        income = sum(t.amount for t in transactions if t.type == 'income')
        expenses = sum(t.amount for t in transactions if t.type == 'expense')
        net = income - expenses

        # Calculate trends (compared to previous period)
        prev_start = start_date - (end_date - start_date)
        prev_transactions = Transaction.query.filter(
            Transaction.date.between(prev_start, start_date)
        ).all()
        prev_income = sum(t.amount for t in prev_transactions if t.type == 'income')
        prev_expenses = sum(t.amount for t in prev_transactions if t.type == 'expense')
        
        # Calculate percentage changes
        income_change = ((income - prev_income) / prev_income * 100) if prev_income > 0 else 0
        expense_change = ((expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
        net_change = income_change - expense_change

        # Get category-wise budget data
        budgets = Budget.query.all()
        budget_data = []
        for budget in budgets:
            spent = sum(t.amount for t in transactions 
                       if t.type == 'expense' and t.category == budget.category)
            budget_data.append({
                'category': budget.category,
                'budget': budget.budget_amount,
                'spent': spent,
                'remaining': budget.budget_amount - spent,
                'percentage': (spent / budget.budget_amount * 100) if budget.budget_amount > 0 else 0
            })

        # Get recent transactions
        recent_transactions = [t.to_dict() for t in transactions[-5:]]

        # Prepare chart data
        dates = []
        daily_income = []
        daily_expenses = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime('%Y-%m-%d'))
            day_transactions = [t for t in transactions if t.date.date() == current.date()]
            daily_income.append(sum(t.amount for t in day_transactions if t.type == 'income'))
            daily_expenses.append(sum(t.amount for t in day_transactions if t.type == 'expense'))
            current += timedelta(days=1)

        response_data = {
            'total_income': income,
            'total_expenses': expenses,
            'net_balance': net,
            'trends': {
                'income': income_change,
                'expenses': expense_change,
                'net': net_change
            },
            'budget_overview': budget_data,
            'recent_transactions': recent_transactions,
            'chart_data': {
                'labels': dates,
                'income': daily_income,
                'expenses': daily_expenses
            }
        }

        # Add payroll status for admin/accountant
        if current_user.role in ['admin', 'accountant']:
            upcoming_payroll = Payroll.query.filter(
                Payroll.payment_date > datetime.utcnow()
            ).order_by(Payroll.payment_date).first()
            
            if upcoming_payroll:
                response_data['payroll'] = {
                    'next_date': upcoming_payroll.payment_date.strftime('%Y-%m-%d'),
                    'status': upcoming_payroll.status,
                    'total_amount': upcoming_payroll.salary_amount
                }

        return jsonify(response_data)

    except Exception as e:
        # Log the error
        error_log = AuditLog(
            user_id=current_user.id,
            action='DASHBOARD_DATA_ERROR',
            endpoint='auth.get_dashboard_data',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'time_range': time_range
            }),
            resource_type='dashboard',
            resource_id=None
        )
        db.session.add(error_log)
        db.session.commit()
        
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@auth_bp.route('/api/financial-alerts')
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def get_financial_alerts():
    """Get financial alerts"""
    alerts = []
    
    # Check budget overruns
    budgets = Budget.query.all()
    for budget in budgets:
        spent = sum(t.amount for t in Transaction.query.filter_by(
            category=budget.category,
            type='expense'
        ).filter(Transaction.date >= datetime.now() - timedelta(days=30)).all())
        if spent > budget.budget_amount:
            alerts.append({
                'type': 'warning',
                'message': f'Budget exceeded for {budget.category}',
                'details': f'Spent ${spent:.2f} of ${budget.budget_amount:.2f} budget'
            })
        elif spent > (budget.budget_amount * 0.8):
            alerts.append({
                'type': 'info',
                'message': f'Budget threshold reached for {budget.category}',
                'details': f'Used {(spent/budget.budget_amount*100):.1f}% of budget'
            })
    
    # Check upcoming payroll
    upcoming_payroll = Payroll.query.filter(
        Payroll.payment_date > datetime.now(),
        Payroll.payment_date <= datetime.now() + timedelta(days=7),
        Payroll.status == 'pending'
    ).all()
    
    for payroll in upcoming_payroll:
        alerts.append({
            'type': 'info',
            'message': 'Upcoming payroll payment',
            'details': f'${payroll.salary_amount:.2f} due on {payroll.payment_date.strftime("%Y-%m-%d")}'
        })
    
    return jsonify(alerts)

@auth_bp.route('/api/real-time-alerts')
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def get_real_time_alerts():
    """Get real-time financial alerts for the user"""
    alerts = []
    
    # Check for budget overruns
    budgets = Budget.query.all()
    for budget in budgets:
        total_expenses = db.session.query(db.func.sum(Transaction.amount))\
            .filter(Transaction.type == 'expense',
                   Transaction.category == budget.category)\
            .scalar() or 0
        
        if total_expenses >= budget.budget_amount * 0.9:  # 90% of budget
            alert_type = 'danger' if total_expenses >= budget.budget_amount else 'warning'
            alerts.append({
                'type': alert_type,
                'message': f'Budget Alert: {budget.category}',
                'details': f'You have used {(total_expenses/budget.budget_amount)*100:.1f}% of your {budget.category} budget'
            })
    
    # Check for upcoming payments (within next 7 days)
    upcoming_date = datetime.utcnow() + timedelta(days=7)
    upcoming_payments = Transaction.query\
        .filter(Transaction.type == 'expense',
               Transaction.date <= upcoming_date,
               Transaction.status == 'pending')\
        .all()
    
    for payment in upcoming_payments:
        alerts.append({
            'type': 'info',
            'message': f'Upcoming Payment: {payment.category}',
            'details': f'Payment of ${payment.amount:.2f} due on {payment.date.strftime("%Y-%m-%d")}'
        })
    
    return jsonify(alerts)

@auth_bp.route('/api/notifications')
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def get_notifications():
    """Get unread notifications and alerts"""
    unread_count = 0
    alerts = []
    
    # Get all transactions from the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    transactions = Transaction.query.filter(Transaction.date >= thirty_days_ago).all()
    
    # Get all budgets
    budgets = Budget.query.all()
    
    # Calculate monthly spending for each budget category
    budget_spending = {}
    for transaction in transactions:
        if transaction.type == 'expense':
            if transaction.category not in budget_spending:
                budget_spending[transaction.category] = 0
            budget_spending[transaction.category] += transaction.amount
    
    # Check each budget category for alerts
    for budget in budgets:
        monthly_spent = budget_spending.get(budget.category, 0)
        
        # Alert if spending is over 80% of budget
        if monthly_spent > budget.budget_amount * 0.8:
            alerts.append({
                'type': 'warning',
                'message': f'Budget alert for {budget.category}',
                'details': f'Used {(monthly_spent/budget.budget_amount*100):.1f}% of budget'
            })
            unread_count += 1
        # Info if spending is over 50% of budget
        elif monthly_spent > budget.budget_amount * 0.5:
            alerts.append({
                'type': 'info',
                'message': f'Budget threshold warning for {budget.category}',
                'details': f'Used {(monthly_spent/budget.budget_amount*100):.1f}% of budget'
            })
            unread_count += 1
    
    return jsonify({
        'unread': unread_count,
        'alerts': alerts
    })

@auth_bp.route('/api/mark-notifications-read', methods=['POST'])
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def mark_notifications_read():
    """Mark all notifications as read"""
    return jsonify({'status': 'success'})

@auth_bp.route('/api/refresh-csrf', methods=['GET'])
@login_required
def refresh_csrf():
    """Endpoint to refresh CSRF token for long-running sessions"""
    try:
        # Log the CSRF token refresh attempt
        audit_log = AuditLog(
            user_id=current_user.id,
            action='CSRF_TOKEN_REFRESH',
            endpoint='auth.refresh_csrf',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'username': current_user.username
            }),
            resource_type='csrf',
            resource_id=None
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'csrf_token': generate_csrf()})
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='CSRF_TOKEN_REFRESH_ERROR',
            endpoint='auth.refresh_csrf',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'username': current_user.username
            }),
            resource_type='csrf',
            resource_id=None
        )
        db.session.add(error_log)
        db.session.commit()
        
        return jsonify({'error': 'Failed to refresh CSRF token'}), 500

@auth_bp.route('/users')
@login_required
@admin_required
def user_list():
    try:
        users = User.query.all()
        
        # Log access to user list
        audit_log = AuditLog(
            user_id=current_user.id,
            action='USER_LIST_ACCESSED',
            resource_type='users',
            resource_id=None,
            details=json.dumps({
                'accessed_by': current_user.username,
                'user_count': len(users)
            }),
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return render_template('admin/users.html', users=users)
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_LIST_ERROR',
            resource_type='users',
            resource_id=None,
            details=json.dumps({
                'error': str(e),
                'accessed_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error loading user list.', 'error')
        return redirect(url_for('auth.dashboard'))

@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        form = UserEditForm(original_email=user.email)

        if request.method == 'GET':
            # Pre-populate form with user data
            form.name.data = user.name
            form.email.data = user.email
            form.role.data = user.role
            form.department.data = user.department
            form.position.data = user.position
        
        if form.validate_on_submit():
            # Update user details
            user.email = form.email.data
            user.name = form.name.data
            user.role = form.role.data
            user.department = form.department.data
            user.position = form.position.data
            
            # Update password if provided
            if form.password.data:
                user.set_password(form.password.data)

            # Log user update
            audit_log = AuditLog(
                user_id=current_user.id,
                action='USER_UPDATED',
                endpoint='auth.edit_user',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'updated_user_id': user_id,
                    'updated_username': user.username,
                    'updated_role': user.role,
                    'updated_by': current_user.username,
                    'password_changed': bool(form.password.data)
                }),
                resource_type='users',
                resource_id=str(user_id)
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('auth.user_list'))
        elif request.method == 'POST':
            # If form validation failed, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
        
        return render_template('admin/edit_user.html', user=user, form=form)

    except Exception as e:
        db.session.rollback()  # Rollback any failed changes
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_UPDATE_ERROR',
            endpoint='auth.edit_user',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'attempted_user_id': user_id,
                'updated_by': current_user.username
            }),
            resource_type='users',
            resource_id=str(user_id)
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error updating user. Please try again.', 'error')
        return redirect(url_for('auth.user_list'))

@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        # Prevent self-deletion
        if current_user.id == user_id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('auth.user_list'))
        
        user = User.query.get_or_404(user_id)
        
        # Store user details for audit log before deletion
        user_details = {
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'department': user.department
        }
        
        # Delete user
        db.session.delete(user)
        
        # Log user deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            action='USER_DELETED',
            endpoint='auth.delete_user',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'deleted_user_details': user_details,
                'deleted_by': current_user.username
            }),
            resource_type='users',
            resource_id=str(user_id)
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash('User deleted successfully!', 'success')
        return redirect(url_for('auth.user_list'))

    except Exception as e:
        db.session.rollback()
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_DELETION_ERROR',
            endpoint='auth.delete_user',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'error': str(e),
                'attempted_user_id': user_id,
                'deleted_by': current_user.username
            }),
            resource_type='users',
            resource_id=str(user_id)
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error deleting user. Please try again.', 'error')
        return redirect(url_for('auth.user_list'))

@auth_bp.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    try:
        form = UserForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data,
                name=form.name.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            
            # Log user creation
            audit_log = AuditLog(
                user_id=current_user.id,
                action='USER_CREATED',
                resource_type='users',
                resource_id=str(user.id),
                details=json.dumps({
                    'created_username': user.username,
                    'created_role': user.role,
                    'created_by': current_user.username
                }),
                ip_address=request.remote_addr
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('User added successfully.', 'success')
            return redirect(url_for('auth.admin_user_management'))
        
        return render_template('admin/add_user.html', form=form)
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_CREATION_ERROR',
            resource_type='users',
            resource_id=None,
            details=json.dumps({
                'error': str(e),
                'accessed_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error adding user.', 'error')
        return redirect(url_for('auth.admin_user_management'))

@auth_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        form = UserForm(obj=user)
        
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            user.name = form.name.data
            
            if form.password.data:
                user.set_password(form.password.data)
            
            # Log user update
            audit_log = AuditLog(
                user_id=current_user.id,
                action='USER_UPDATED',
                resource_type='users',
                resource_id=str(user.id),
                details=json.dumps({
                    'updated_username': user.username,
                    'updated_role': user.role,
                    'updated_by': current_user.username
                }),
                ip_address=request.remote_addr
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('User updated successfully.', 'success')
            return redirect(url_for('auth.admin_user_management'))
        
        return render_template('admin/edit_user.html', form=form, user=user)
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_UPDATE_ERROR',
            resource_type='users',
            resource_id=str(user_id),
            details=json.dumps({
                'error': str(e),
                'accessed_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error updating user.', 'error')
        return redirect(url_for('auth.admin_user_management'))

@auth_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        if user.id == current_user.id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('auth.admin_user_management'))
        
        # Log user deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            action='USER_DELETED',
            resource_type='users',
            resource_id=str(user.id),
            details=json.dumps({
                'deleted_username': user.username,
                'deleted_role': user.role,
                'deleted_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        
        db.session.delete(user)
        db.session.add(audit_log)
        db.session.commit()
        
        flash('User deleted successfully.', 'success')
        return redirect(url_for('auth.admin_user_management'))
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_DELETION_ERROR',
            resource_type='users',
            resource_id=str(user_id),
            details=json.dumps({
                'error': str(e),
                'accessed_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error deleting user.', 'error')
        return redirect(url_for('auth.admin_user_management'))

@auth_bp.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    return render_template('auth/transactions.html', transactions=transactions)

@auth_bp.route('/budgets')
@login_required
def budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return render_template('auth/budgets.html', budgets=budgets)

@auth_bp.route('/reports')
@login_required
def reports():
    return render_template('auth/reports.html')

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/settings')
@login_required
def settings():
    return render_template('auth/settings.html')

@auth_bp.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin/dashboard.html')

@auth_bp.route('/departments')
@login_required
def department_list():
    """List all departments for admin users"""
    if not current_user.role == 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    departments = Department.query.all()
    return render_template('department/list.html', departments=departments)

@auth_bp.route('/department/<int:dept_id>/employees')
@login_required
def department_employees(dept_id):
    """View department employees and payroll"""
    if dept_id == 0 and current_user.department_id:
        # Redirect to user's own department if they have one
        return redirect(url_for('auth.department_employees', dept_id=current_user.department_id))
    
    department = Department.query.get_or_404(dept_id)
    
    # Check permissions
    if not current_user.can_view_department_data(dept_id):
        flash('You do not have permission to view this department\'s employee data.', 'error')
        return redirect(url_for('auth.dashboard'))
    
    employees = User.query.filter_by(department_id=dept_id).all()
    
    # Get latest payroll for each employee
    employee_payroll = {}
    for employee in employees:
        latest_payroll = Payroll.query.filter_by(employee_id=employee.id).order_by(Payroll.date.desc()).first()
        employee_payroll[employee.id] = latest_payroll

    return render_template('department/employees.html', 
                         department=department, 
                         employees=employees,
                         employee_payroll=employee_payroll)

# Department Management API Routes
@auth_bp.route('/api/departments', methods=['GET', 'POST'])
@login_required
def api_departments():
    """API endpoint for department management"""
    if not current_user.role == 'admin':
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'POST':
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Department name is required'}), 400
            
        # Create new department
        department = Department(
            name=data['name'],
            budget_limit=data.get('budget_limit', 0.0),
            manager_id=data.get('manager_id')
        )
        
        try:
            db.session.add(department)
            db.session.commit()
            return jsonify({'message': 'Department created successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # GET method - return all departments
    departments = Department.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'budget_limit': d.budget_limit,
        'manager_id': d.manager_id,
        'monthly_expenses': d.monthly_expenses
    } for d in departments])

@auth_bp.route('/api/departments/<int:dept_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_department(dept_id):
    """API endpoint for individual department operations"""
    if not current_user.role == 'admin':
        return jsonify({'error': 'Access denied'}), 403

    department = Department.query.get_or_404(dept_id)

    if request.method == 'GET':
        return jsonify({
            'id': department.id,
            'name': department.name,
            'budget_limit': department.budget_limit,
            'manager_id': department.manager_id,
            'monthly_expenses': department.monthly_expenses
        })

    elif request.method == 'PUT':
        data = request.get_json()
        
        if 'name' in data:
            department.name = data['name']
        if 'budget_limit' in data:
            department.budget_limit = data['budget_limit']
        if 'manager_id' in data:
            department.manager_id = data['manager_id']
            
        try:
            db.session.commit()
            return jsonify({'message': 'Department updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    elif request.method == 'DELETE':
        # Check if department has employees
        if department.employees:
            return jsonify({'error': 'Cannot delete department with active employees'}), 400
            
        try:
            db.session.delete(department)
            db.session.commit()
            return jsonify({'message': 'Department deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

# Language and Theme Routes
@auth_bp.route('/api/preferences/language', methods=['POST'])
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def set_language():
    data = request.get_json()
    language = data.get('language', 'en')
    if language not in ['en', 'es']:
        return jsonify({'error': 'Invalid language'}), 400
    
    session['language'] = language
    return jsonify({'status': 'success'})

@auth_bp.route('/api/preferences/theme', methods=['POST'])
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def set_theme():
    data = request.get_json()
    theme = data.get('theme', 'light')
    if theme not in ['light', 'dark']:
        return jsonify({'error': 'Invalid theme'}), 400
    
    session['theme'] = theme
    return jsonify({'status': 'success'})

@auth_bp.route('/api/notifications/settings', methods=['GET', 'POST'])
@login_required
@limiter.limit("60 per minute")  # Rate limiting for API endpoints
def notification_settings():
    if request.method == 'POST':
        data = request.get_json()
        enabled = data.get('enabled', False)
        session['notifications_enabled'] = enabled
        return jsonify({'status': 'success'})
    
    return jsonify({
        'enabled': session.get('notifications_enabled', False)
    })

# Update the context processor to include language and theme
@auth_bp.context_processor
def inject_user_preferences():
    if not current_user.is_authenticated:
        return {
            'language': 'en',
            'theme': 'light',
            'notifications_enabled': True
        }
    return {
        'language': session.get('language', 'en'),
        'theme': session.get('theme', 'light'),
        'notifications_enabled': session.get('notifications_enabled', True)
    }

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role == 'manager':
            flash('You must be a manager to access this page.', 'error')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/manager/dashboard')
@login_required
@manager_required
def manager_dashboard():
    """Manager dashboard showing department performance and pending approvals"""
    if current_user.managed_department:
        department = current_user.managed_department
        
        # Get department statistics
        total_budget = department.budget_limit
        pending_transactions = Transaction.query.filter_by(
            department_id=department.id,
            status='pending'
        ).all()
        
        # Calculate department expenses
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.department_id == department.id,
            Transaction.type == 'expense',
            Transaction.status == 'approved',
            Transaction.date >= month_start
        ).scalar() or 0
        
        # Get department employees
        employees = User.query.filter_by(department_id=department.id).all()
        
        # Get upcoming payroll
        upcoming_payroll = Payroll.query.filter(
            Payroll.employee_id.in_([emp.id for emp in employees]),
            Payroll.status == 'pending'
        ).all()
        
        return render_template('manager/dashboard.html',
                             department=department,
                             total_budget=total_budget,
                             monthly_expenses=monthly_expenses,
                             pending_transactions=pending_transactions,
                             employees=employees,
                             upcoming_payroll=upcoming_payroll)
    
    flash('No department assigned to manage.', 'error')
    return redirect(url_for('auth.dashboard'))

@auth_bp.route('/department/<int:dept_id>/transactions')
@login_required
def department_transactions(dept_id):
    """View department transactions"""
    if not current_user.can_view_department_data(dept_id):
        flash('You do not have permission to view this department\'s transactions.', 'error')
        return redirect(url_for('auth.dashboard'))
    
    department = Department.query.get_or_404(dept_id)
    transactions = Transaction.query.filter_by(department_id=dept_id).order_by(Transaction.date.desc()).all()
    
    return render_template('department/transactions.html',
                         department=department,
                         transactions=transactions)

@auth_bp.route('/manager/approve-transaction/<int:transaction_id>', methods=['POST'])
@login_required
@manager_required
def approve_transaction(transaction_id):
    """Approve or reject a transaction"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if not current_user.can_manage_department(transaction.department_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Invalid action'}), 400
    
    transaction.status = 'approved' if action == 'approve' else 'rejected'
    transaction.approver_id = current_user.id
    transaction.approval_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'Transaction {action}d successfully'
    })

@auth_bp.route('/department/<int:dept_id>/budget')
@login_required
def department_budget(dept_id):
    """View department budget and expenses"""
    if not current_user.can_view_department_data(dept_id):
        flash('You do not have permission to view this department\'s budget.', 'error')
        return redirect(url_for('auth.dashboard'))
    
    department = Department.query.get_or_404(dept_id)
    
    # Get monthly expenses
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    monthly_expenses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.department_id == dept_id,
        Transaction.type == 'expense',
        Transaction.status == 'approved',
        Transaction.date >= month_start
    ).scalar() or 0
    
    # Get expenses by category
    expenses_by_category = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.department_id == dept_id,
        Transaction.type == 'expense',
        Transaction.status == 'approved',
        Transaction.date >= month_start
    ).group_by(Transaction.category).all()
    
    return render_template('department/budget.html',
                         department=department,
                         monthly_expenses=monthly_expenses,
                         expenses_by_category=expenses_by_category)

@auth_bp.route('/manager/set-department-budget', methods=['POST'])
@login_required
@manager_required
def set_department_budget():
    """Set or update department budget"""
    if not current_user.managed_department:
        return jsonify({'error': 'No department assigned'}), 400
    
    try:
        budget_limit = float(request.form.get('budget_limit', 0))
        if budget_limit < 0:
            return jsonify({'error': 'Budget cannot be negative'}), 400
        
        current_user.managed_department.budget_limit = budget_limit
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Department budget updated successfully'
        })
    except ValueError:
        return jsonify({'error': 'Invalid budget amount'}), 400

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate reset token
            token = user.get_reset_password_token()
            # Send password reset email
            send_password_reset_email(user, token)
            flash('Check your email for instructions to reset your password.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Email address not found.', 'error')
    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password_with_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_with_token.html', form=form)

@auth_bp.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_user_management():
    try:
        users = User.query.all()
        
        # Log access to user management
        audit_log = AuditLog(
            user_id=current_user.id,
            action='USER_MANAGEMENT_ACCESSED',
            resource_type='users',
            resource_id=None,
            details=json.dumps({
                'accessed_by': current_user.username,
                'user_count': len(users)
            }),
            ip_address=request.remote_addr
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return render_template('admin/user_management.html', users=users)
    except Exception as e:
        # Log error
        error_log = AuditLog(
            user_id=current_user.id,
            action='USER_MANAGEMENT_ERROR',
            resource_type='users',
            resource_id=None,
            details=json.dumps({
                'error': str(e),
                'accessed_by': current_user.username
            }),
            ip_address=request.remote_addr
        )
        db.session.add(error_log)
        db.session.commit()
        
        flash('Error accessing user management.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/transaction/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@finance_required
def edit_transaction(id):
    """Edit an existing transaction"""
    transaction = Transaction.query.get_or_404(id)
    if request.method == 'POST':
        try:
            transaction.type = request.form['type']
            transaction.amount = float(request.form['amount'])
            transaction.description = request.form['description']
            transaction.category = request.form['category']
            transaction.department_id = request.form['department_id']
            transaction.date = datetime.strptime(request.form['date'], '%Y-%m-%d') if request.form['date'] else None
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='UPDATE',
                endpoint='main.edit_transaction',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'type': transaction.type,
                    'amount': transaction.amount,
                    'category': transaction.category
                }),
                resource_type='transaction',
                resource_id=str(transaction.id)
            )
            db.session.add(audit_log)
            
            db.session.commit()
            flash('Transaction updated successfully.', 'success')
            return redirect(url_for('main.view_transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating transaction: {str(e)}', 'error')
    
    budgets = Budget.query.all()
    departments = Department.query.all()
    return render_template('transaction_form.html', 
                         budgets=budgets,
                         departments=departments,
                         transaction=transaction)

@main_bp.route('/transaction/<int:id>', methods=['DELETE'])
@login_required
@finance_required
def delete_transaction(id):
    """Delete a transaction via AJAX"""
    transaction = Transaction.query.get_or_404(id)
    
    # Check if user has permission to delete this transaction
    if current_user.role not in ['admin', 'finance'] or \
       (current_user.role == 'finance' and transaction.department_id != current_user.department_id):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        # Add audit log before deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            action='DELETE',
            endpoint='main.delete_transaction',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'type': transaction.type,
                'amount': transaction.amount,
                'category': transaction.category,
                'department_id': transaction.department_id
            }),
            resource_type='transaction',
            resource_id=str(transaction.id)
        )
        db.session.add(audit_log)
        
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting transaction {id}: {str(e)}")
        return jsonify({'error': 'Failed to delete transaction'}), 500

@main_bp.route('/budgets')
@login_required
@finance_required
def get_budgets():
    """View all budgets with their utilization"""
    budgets = Budget.query.all()
    budget_data = []
    
    for budget in budgets:
        # Calculate total expenses for this budget category
        total_expenses = sum(t.amount for t in budget.transactions 
                           if t.type == 'expense' and t.status == 'approved')
        
        # Calculate percentage utilized
        if budget.budget_amount > 0:
            utilization = (total_expenses / budget.budget_amount) * 100
        else:
            utilization = 0
        
        # Add status based on utilization
        if utilization >= 90:
            status = 'danger'
        elif utilization >= 75:
            status = 'warning'
        else:
            status = 'good'
        
        budget_data.append({
            'category': budget.category,
            'budget_amount': budget.budget_amount,
            'total_expenses': total_expenses,
            'utilization': utilization,
            'status': status
        })
    
    return render_template('budgets.html', budgets=budget_data)

@main_bp.route('/budget/add', methods=['GET', 'POST'])
@login_required
@finance_required
def add_budget():
    """Add a new budget category"""
    if request.method == 'POST':
        try:
            category = request.form['category']
            budget_amount = float(request.form['budget_amount'])
            
            # Check if category already exists
            existing_budget = Budget.query.filter_by(category=category).first()
            if existing_budget:
                flash('Budget category already exists.', 'error')
                return redirect(url_for('main.get_budgets'))
            
            budget = Budget(category=category, budget_amount=budget_amount)
            db.session.add(budget)
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='CREATE',
                endpoint='main.add_budget',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'category': category,
                    'budget_amount': budget_amount
                }),
                resource_type='budget',
                resource_id=category
            )
            db.session.add(audit_log)
            
            db.session.commit()
            flash('Budget category added successfully.', 'success')
            return redirect(url_for('main.get_budgets'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding budget category: {str(e)}', 'error')
    
    return render_template('budget_form.html', budget=None)

@main_bp.route('/budget/edit/<category>', methods=['GET', 'POST'])
@login_required
@finance_required
def edit_budget(category):
    """Edit an existing budget"""
    budget = Budget.query.get_or_404(category)
    if request.method == 'POST':
        try:
            budget.budget_amount = float(request.form['budget_amount'])
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='UPDATE',
                endpoint='main.edit_budget',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'category': category,
                    'budget_amount': budget.budget_amount
                }),
                resource_type='budget',
                resource_id=category
            )
            db.session.add(audit_log)
            
            db.session.commit()
            flash('Budget updated successfully.', 'success')
            return redirect(url_for('main.get_budgets'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating budget: {str(e)}', 'error')
    
    return render_template('budget_form.html', budget=budget)

@main_bp.route('/budget/delete/<category>', methods=['POST'])
@login_required
@finance_required
def delete_budget(category):
    """Delete a budget category"""
    budget = Budget.query.get_or_404(category)
    
    # Check if there are any transactions using this budget category
    transactions = Transaction.query.filter_by(category=budget.category).first()
    if transactions:
        flash('Cannot delete budget category that has transactions.', 'error')
        return redirect(url_for('main.get_budgets'))
    
    try:
        # Add audit log before deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            action='DELETE',
            endpoint='main.delete_budget',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'category': category,
                'budget_amount': budget.budget_amount
            }),
            resource_type='budget',
            resource_id=category
        )
        db.session.add(audit_log)
        
        db.session.delete(budget)
        db.session.commit()
        flash('Budget category deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting budget category: {str(e)}', 'error')
    
    return redirect(url_for('main.get_budgets'))

@main_bp.route('/payroll')
@login_required
@finance_required
def get_payroll_overview():
    """View payroll overview and history"""
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get current month's payroll data
    current_payroll = Payroll.query.filter(
        Payroll.payment_date >= current_month,
        Payroll.payment_date < current_month.replace(month=current_month.month + 1)
    ).all()
    
    # Calculate total payroll for current month
    total_current = sum(p.salary_amount for p in current_payroll)
    
    # Get historical data for the past 6 months
    historical_data = []
    for i in range(6):
        month = current_month.replace(month=current_month.month - i)
        if month.month > current_month.month:
            month = month.replace(year=month.year - 1)
        
        month_payroll = Payroll.query.filter(
            Payroll.payment_date >= month,
            Payroll.payment_date < month.replace(month=month.month + 1)
        ).all()
        
        total = sum(p.salary_amount for p in month_payroll)
        historical_data.append({
            'month': month.strftime('%B %Y'),
            'total': total,
            'count': len(month_payroll)
        })
    
    return render_template('payroll.html',
                         current_payroll=current_payroll,
                         total_current=total_current,
                         historical_data=historical_data)

@main_bp.route('/payroll/add', methods=['GET', 'POST'])
@login_required
@finance_required
def add_payroll():
    """Add a new payroll record"""
    if request.method == 'POST':
        try:
            employee_id = request.form['employee_id']
            salary_amount = float(request.form['salary_amount'])
            payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d')
            
            # Check if employee exists
            employee = User.query.get(employee_id)
            if not employee:
                flash('Employee not found.', 'error')
                return redirect(url_for('main.get_payroll_overview'))
            
            # Check if payroll record already exists for this month
            existing_payroll = Payroll.query.filter(
                Payroll.employee_id == employee_id,
                Payroll.payment_date.between(
                    payment_date.replace(day=1),
                    payment_date.replace(day=1, month=payment_date.month + 1)
                )
            ).first()
            
            if existing_payroll:
                flash('Payroll record already exists for this month.', 'error')
                return redirect(url_for('main.get_payroll_overview'))
            
            payroll = Payroll(
                employee_id=employee_id,
                salary_amount=salary_amount,
                payment_date=payment_date
            )
            db.session.add(payroll)
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='CREATE',
                endpoint='main.add_payroll',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'employee_id': employee_id,
                    'salary_amount': salary_amount,
                    'payment_date': payment_date.strftime('%Y-%m-%d')
                }),
                resource_type='payroll',
                resource_id=None
            )
            db.session.add(audit_log)
            
            db.session.commit()
            flash('Payroll record added successfully.', 'success')
            return redirect(url_for('main.get_payroll_overview'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding payroll record: {str(e)}', 'error')
    
    employees = User.query.filter_by(role='employee').all()
    return render_template('payroll_form.html', payroll=None, employees=employees)

@main_bp.route('/payroll/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@finance_required
def edit_payroll(id):
    """Edit an existing payroll record"""
    payroll = Payroll.query.get_or_404(id)
    if request.method == 'POST':
        try:
            payroll.salary_amount = float(request.form['salary_amount'])
            payroll.payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d')
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='UPDATE',
                endpoint='main.edit_payroll',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'employee_id': payroll.employee_id,
                    'salary_amount': payroll.salary_amount,
                    'payment_date': payroll.payment_date.strftime('%Y-%m-%d')
                }),
                resource_type='payroll',
                resource_id=str(payroll.id)
            )
            db.session.add(audit_log)
            
            db.session.commit()
            flash('Payroll record updated successfully.', 'success')
            return redirect(url_for('main.get_payroll_overview'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating payroll record: {str(e)}', 'error')
    
    employees = User.query.filter_by(role='employee').all()
    return render_template('payroll_form.html', payroll=payroll, employees=employees)

@main_bp.route('/payroll/delete/<int:id>', methods=['POST'])
@login_required
@finance_required
def delete_payroll(id):
    """Delete a payroll record"""
    payroll = Payroll.query.get_or_404(id)
    try:
        # Add audit log before deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            action='DELETE',
            endpoint='main.delete_payroll',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow(),
            details=json.dumps({
                'employee_id': payroll.employee_id,
                'salary_amount': payroll.salary_amount,
                'payment_date': payroll.payment_date.strftime('%Y-%m-%d')
            }),
            resource_type='payroll',
            resource_id=str(payroll.id)
        )
        db.session.add(audit_log)
        
        db.session.delete(payroll)
        db.session.commit()
        flash('Payroll record deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting payroll record: {str(e)}', 'error')
    return redirect(url_for('main.get_payroll_overview'))

@main_bp.route('/transactions')
@login_required
@finance_required
def view_transactions():
    """View all transactions with filtering options"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    transaction_type = request.args.get('type')
    status = request.args.get('status')
    department_id = request.args.get('department_id')
    
    # Base query
    query = Transaction.query
    
    # Apply filters
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if status:
        query = query.filter(Transaction.status == status)
    if department_id:
        query = query.filter(Transaction.department_id == int(department_id))
    elif not current_user.role == 'admin':
        # Non-admin users can only see their department's transactions
        query = query.filter(Transaction.department_id == current_user.department_id)
    
    # Get results with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    transactions = query.order_by(Transaction.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get departments for filtering
    departments = Department.query.all() if current_user.role == 'admin' else [current_user.department]
    
    # Get transaction categories from budgets
    categories = [budget.category for budget in Budget.query.all()]
    
    return render_template('transactions.html',
                         transactions=transactions,
                         departments=departments,
                         categories=categories,
                         filters={
                             'start_date': start_date,
                             'end_date': end_date,
                             'type': transaction_type,
                             'status': status,
                             'department_id': department_id
                         })

@main_bp.route('/transaction/<int:id>')
@login_required
def view_transaction(id):
    """View details of a specific transaction"""
    transaction = Transaction.query.get_or_404(id)
    
    # Check if user has permission to view this transaction
    if not current_user.role == 'admin' and transaction.department_id != current_user.department_id:
        abort(403)
    
    # Get audit logs for this transaction
    audit_logs = AuditLog.query.filter_by(
        resource_type='transaction',
        resource_id=str(transaction.id)
    ).order_by(AuditLog.created_at.desc()).all()
    
    return render_template('transaction_detail.html',
                         transaction=transaction,
                         audit_logs=audit_logs)

@main_bp.route('/transaction/add', methods=['GET', 'POST'])
@login_required
@finance_required
def add_transaction():
    """Add a new transaction"""
    if request.method == 'POST':
        try:
            # Validate department access
            department_id = request.form.get('department_id')
            if not current_user.role == 'admin' and int(department_id) != current_user.department_id:
                abort(403)
            
            transaction = Transaction(
                type=request.form['type'],
                amount=float(request.form['amount']),
                description=request.form['description'],
                category=request.form['category'],
                department_id=department_id,
                creator_id=current_user.id,
                date=datetime.strptime(request.form['date'], '%Y-%m-%d') if request.form['date'] else datetime.now(),
                status='pending' if current_user.role != 'admin' else 'approved'
            )
            
            # Add audit log
            audit_log = AuditLog(
                user_id=current_user.id,
                action='CREATE',
                endpoint='main.add_transaction',
                ip_address=request.remote_addr,
                timestamp=datetime.utcnow(),
                details=json.dumps({
                    'type': transaction.type,
                    'amount': transaction.amount,
                    'category': transaction.category,
                    'department_id': transaction.department_id
                }),
                resource_type='transaction',
                resource_id=None
            )
            db.session.add(audit_log)
            
            db.session.add(transaction)
            db.session.commit()
            flash('Transaction added successfully.', 'success')
            return redirect(url_for('main.view_transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding transaction: {str(e)}', 'error')
    
    # Get available budgets and departments
    budgets = Budget.query.all()
    departments = Department.query.all() if current_user.role == 'admin' else [current_user.department]
    
    return render_template('transaction_form.html',
                         budgets=budgets,
                         departments=departments,
                         transaction=None)

@auth_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications"""
    # Get all notifications for the current user
    notifications = []
    
    # Get all transactions from the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    transactions = Transaction.query.filter(Transaction.date >= thirty_days_ago).all()
    
    # Get all budgets
    budgets = Budget.query.all()
    
    # Calculate monthly spending for each budget category
    budget_spending = {}
    for transaction in transactions:
        if transaction.type == 'expense':
            if transaction.category not in budget_spending:
                budget_spending[transaction.category] = 0
            budget_spending[transaction.category] += transaction.amount
    
    # Check each budget category for alerts
    for budget in budgets:
        monthly_spent = budget_spending.get(budget.category, 0)
        
        # Alert if spending is over 80% of budget
        if monthly_spent > budget.budget_amount * 0.8:
            notifications.append({
                'id': f'budget_{budget.id}_warning',
                'type': 'warning',
                'message': f'Budget alert for {budget.category}',
                'details': f'Used {(monthly_spent/budget.budget_amount*100):.1f}% of budget',
                'timestamp': datetime.utcnow()
            })
        # Info if spending is over 50% of budget
        elif monthly_spent > budget.budget_amount * 0.5:
            notifications.append({
                'id': f'budget_{budget.id}_info',
                'type': 'info',
                'message': f'Budget threshold warning for {budget.category}',
                'details': f'Used {(monthly_spent/budget.budget_amount*100):.1f}% of budget',
                'timestamp': datetime.utcnow()
            })
    
    # Sort notifications by timestamp
    notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('notifications.html', notifications=notifications)

@auth_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    try:
        # In a real application, you would update the notification status in the database
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        # In a real application, you would update all notifications status in the database
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
