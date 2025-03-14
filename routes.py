from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from models import Income, Expense  # Ensure these models exist with necessary fields
from flask_login import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/dashboard')
@login_required  # Ensuring only authenticated users access the dashboard
def dashboard():
    total_income = db.session.query(db.func.sum(Income.amount)).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    net_balance = total_income - total_expense
    return render_template('dashboard.html', total_income=total_income, total_expense=total_expense, net_balance=net_balance)

@auth_bp.route('/add_income', methods=['GET', 'POST'])
@login_required
def add_income():
    if request.method == 'POST':
        amount = request.form.get('amount')
        category = request.form.get('category')
        if not amount or float(amount) <= 0:
            flash('Please enter a valid positive amount.')
            return redirect(url_for('auth.add_income'))
        
        new_income = Income(amount=float(amount), category=category)
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
        category = request.form.get('category')
        if not amount or float(amount) <= 0:
            flash('Please enter a valid positive amount.')
            return redirect(url_for('auth.add_expense'))
        
        new_expense = Expense(amount=float(amount), category=category)
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully!')
        return redirect(url_for('auth.dashboard'))
    
    return render_template('add_expense.html')
