from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Income, Expense, User
from extensions import db
from flask_login import login_user, logout_user, login_required, current_user

# Define the blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('auth.register'))

        new_user = User(username=username)
        new_user.set_password(password)  # Hash the password
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('auth.dashboard'))
        
        flash('Login failed. Check your username and password.')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/add_income', methods=['GET', 'POST'])
@login_required
def add_income():
    if request.method == 'POST':
        amount = request.form.get('amount')
        description = request.form.get('description')
        new_income = Income(amount=amount, description=description, user_id=current_user.id)
        db.session.add(new_income)
        db.session.commit()
        flash('Income added successfully!')
        return redirect(url_for('auth.dashboard'))
    return render_template('add_income.html')

@auth_bp.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        amount = request.form.get('amount')
        description = request.form.get('description')
        new_expense = Expense(amount=amount, description=description, user_id=current_user.id)
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully!')
        return redirect(url_for('auth.dashboard'))
    return render_template('add_expense.html')

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@auth_bp.route('/view_records')
@login_required
def view_records():
    income_records = Income.query.filter_by(user_id=current_user.id).all()
    expense_records = Expense.query.filter_by(user_id=current_user.id).all()
    return render_template('view_records.html', income_records=income_records, expense_records=expense_records)
