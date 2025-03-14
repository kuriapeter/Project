
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify, send_file
from models import (
    get_financial_overview, get_kpi_data, get_yearly_income_expenses,
    add_transaction, get_monthly_income_expenses, get_expense_breakdown,
    get_top_spending_categories, get_budgets, set_budget,
    get_spending_by_category, get_recent_transactions
)
from datetime import datetime
from flask_mysqldb import MySQL
import pymysql
from models import get_alerts
import io
from reportlab.pdfgen import canvas
import pandas as pd
from models import get_payroll_records


app = Flask(__name__, template_folder="templates")
app.config["DEBUG"] = True  
app.secret_key = 'your_secret_key_here'  

# MySQL Database Configuration

    
app.config['MYSQL_HOST'] = 'localhost'  
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = ''  
app.config['MYSQL_DB'] = 'company_finance'  
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  
    
mysql = MySQL(app)  

def get_db_connection():
    return pymysql.connect(host=app.config['MYSQL_HOST'],
                           user=app.config['MYSQL_USER'],
                           password=app.config['MYSQL_PASSWORD'],
                           database=app.config['MYSQL_DB'],
                           cursorclass=pymysql.cursors.DictCursor)



@app.route('/test')
def test_db():
    try:
        connection = mysql.connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        return f"MySQL Test: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/dashboard')
def dashboard():
    financial_data = {
        "total_income": 10000,  # Replace with actual database query
        "total_expenses": 5000,
        "net_profit": 5000,
        "balance": 12000,
        "debts": 3000
    }
    return render_template('dashboard.html', financial_data=financial_data)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction_route():
    if request.method == 'POST':
        trans_type = request.form.get('type')
        amount = request.form.get('amount')
        description = request.form.get('description')
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not trans_type or not amount or not description:
            flash("All fields are required!", "danger")
        else:
            add_transaction(mysql, trans_type, amount, description, date)
            flash("Transaction added successfully!", "success")
            return redirect(url_for('add_transaction_route'))

    return render_template('add_transaction.html')

@app.route('/view_transactions')
def view_transactions():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY date DESC")
    transactions = cur.fetchall()
    cur.close()
    return render_template('view_transactions.html', transactions=transactions)

@app.route('/charts')
def charts_page():
    return render_template('charts.html')

@app.route('/api/monthly_data')
def monthly_data():
    return jsonify(get_monthly_income_expenses(mysql))

@app.route('/api/expense_breakdown')
def expense_breakdown():
    return jsonify(get_expense_breakdown(mysql))

@app.route('/api/top_spending')
def top_spending():
    return jsonify(get_top_spending_categories(mysql))

@app.route('/budgets')
def budgets():
    budgets = get_budgets(mysql)
    spending = get_spending_by_category(mysql)
    budget_data = []
    for budget in budgets:
        spent = next((s["spent"] for s in spending if s["category"] == budget["category"]), 0) or 0
        budget_amount = budget["budget_amount"] or 1  
        percent_used = (spent / budget_amount) * 100
        budget_data.append({
            "category": budget["category"],
            "budget": budget["budget_amount"],
            "spent": spent,
            "percent_used": percent_used,
            "warning": percent_used >= 80
        })

    return render_template('budgets.html', budget_data=budget_data)

@app.route('/set_budget', methods=['POST'])
def set_budget_route():
    category = request.form.get('category')
    amount = float(request.form.get('amount'))
    set_budget(mysql, category, amount)
    flash("Budget updated successfully!", "success")
    return redirect('/budgets')

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        description = request.form.get('description')

        if not category or not amount or not description:
            flash("All fields are required!", "danger")
            return redirect(url_for('add_income'))

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO transactions (category, amount, description, type) VALUES (%s, %s, %s, 'income')",
                        (category, amount, description))
            mysql.connection.commit()
            cur.close()
            flash("Income added successfully!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")

        return redirect(url_for('add_income'))

    return render_template('add_income.html')

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        description = request.form.get('description')

        if not category or not amount or not description:
            flash("All fields are required!", "danger")
            return redirect(url_for('add_expense'))

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO transactions (category, amount, description, type) VALUES (%s, %s, %s, 'expense')",
                        (category, amount, description))
            mysql.connection.commit()
            cur.close()
            flash("Expense added successfully!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")

        return redirect(url_for('add_expense'))

    return render_template('add_expense.html')

@app.route('/api/recent_transactions', methods=['GET'])
def recent_transactions():
    try:
        transactions = get_recent_transactions(mysql)
        formatted_transactions = [
            {
                'date': transaction['date'].strftime('%Y-%m-%d %H:%M:%S'),
                'category': transaction['category'] or 'Uncategorized',
                'amount': float(transaction['amount']),
                'status': transaction['status']
            }
            for transaction in transactions
        ]
        return jsonify(formatted_transactions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/kpi_data')
def kpi_data_api():
    return jsonify(get_kpi_data(mysql))

@app.route('/api/alerts')
def alerts_api():
    return jsonify(get_alerts(mysql))
def get_alerts(mysql):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM alerts")  # Adjust query based on your DB schema
    alerts = cursor.fetchall()
    cursor.close()
    return alerts



# Fetch financial data based on timeframe
import pandas as pd

def fetch_financial_data(timeframe):
    conn = get_db_connection()  # Ensure this function is correctly defined

    timeframe_map = {
        "monthly": "DATE_FORMAT(date, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')",
        "quarterly": "QUARTER(date) = QUARTER(NOW()) AND YEAR(date) = YEAR(NOW())",
        "yearly": "YEAR(date) = YEAR(NOW())"
    }

    query = "SELECT * FROM financial_data"
    if timeframe in timeframe_map:
        query += f" WHERE {timeframe_map[timeframe]}"

    # Ensure `pd.read_sql` is called correctly
    df = pd.read_sql(query, conn)  

    conn.close()
    return df


# Route to render reports page
@app.route('/reports')
def reports_page():
    return render_template('reports.html')

# Export as CSV
@app.route('/export/csv/<timeframe>')
def export_csv(timeframe):
    df = fetch_financial_data(timeframe)
    print(df)  # Check if data exists

    output = io.StringIO()
    df.to_csv("financial_data.csv", index=False)

    output.seek(0)
    
    filename = f"financial_report_{timeframe}.csv"
    return send_file(io.BytesIO(output.getvalue().encode()), as_attachment=True, download_name=filename, mimetype='text/csv')

# Export as Excel
@app.route('/export/excel/<timeframe>')
def export_excel(timeframe):
    df = fetch_financial_data(timeframe)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    output.seek(0)
    
    filename = f"financial_report_{timeframe}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Export as PDF
@app.route('/export/pdf/<timeframe>')
def export_pdf(timeframe):
    df = fetch_financial_data(timeframe)
    output = io.BytesIO()
    p = canvas.Canvas(output)
    
    p.drawString(200, 800, f"Financial Report ({timeframe.capitalize()})")
    
    y_position = 780
    for _, row in df.iterrows():
        p.drawString(50, y_position, f"{row['date']} | {row['category']} | {row['description']} | {row['amount']} | {row['type']}")
        y_position -= 20
    
    p.save()
    output.seek(0)
    
    filename = f"financial_report_{timeframe}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

def fetch_financial_data(timeframe):
    conn = get_db_connection()

    if conn is None:
        raise Exception("Database connection failed. Please check your MySQL connection settings.")

    query = "SELECT * FROM financial_data"

    # Use pandas to read from MySQL
    df = pd.read_sql(query, conn)

    conn.close()
    return df


@app.route('/api/financial_data')
def financial_data_api():
    data = fetch_financial_data(timeframe='monthly')

    if isinstance(data, pd.DataFrame):
        data = data.to_dict(orient='records')  # ✅ Convert DataFrame to JSON-compatible format

    return jsonify(data)

@app.route('/payroll/total', methods=['GET'])
def get_total_payroll():
    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("SELECT SUM(salary_amount) AS total_payroll FROM payroll WHERE status = 'Paid'")
    total_payroll = cursor.fetchone()
    
    conn.close()
    return jsonify({"total_payroll": total_payroll["total_payroll"] if total_payroll["total_payroll"] else 0})

@app.route('/payroll/upcoming', methods=['GET'])
def get_upcoming_payroll():
    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("SELECT employee_id, salary_amount, pay_date FROM payroll WHERE pay_date >= CURDATE() AND status = 'Pending' ORDER BY pay_date ASC")
    upcoming_payroll = cursor.fetchall()
    
    conn.close()
    return jsonify({"upcoming_payroll": upcoming_payroll})

@app.route('/payroll/discrepancies', methods=['GET'])
def get_payroll_discrepancies():
    conn = get_db_connection()
    cursor = conn.cursor()


    # Example logic: Find employees with missing salary payments in the current month
    cursor.execute("""
        SELECT e.id, e.name, p.salary_amount, p.pay_date
        FROM employees e
        LEFT JOIN payroll p ON e.id = p.employee_id AND MONTH(p.pay_date) = MONTH(CURDATE()) AND YEAR(p.pay_date) = YEAR(CURDATE())
        WHERE p.id IS NULL
    """)
    
    discrepancies = cursor.fetchall()
    conn.close()

    return jsonify({"discrepancies": discrepancies})





# Payroll Fix
@app.route('/add_payroll', methods=['GET', 'POST'])
def add_payroll():
    if request.method == 'POST':
        try:
            employee_id = request.form.get('employee_id')
            salary_amount = request.form.get('salary_amount')
            pay_date = request.form.get('pay_date')
            status = request.form.get('status')
            notes = request.form.get('notes')

            if not employee_id or not salary_amount or not pay_date:
                return "Error: Missing required fields", 400

            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO payroll (employee_id, salary_amount, pay_date, status, notes) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (employee_id, salary_amount, pay_date, status, notes))
            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for('payroll_overview'))

        except Exception as e:
            return f"Database Error: {str(e)}", 500

    # If the request is GET, return a payroll form
    return render_template("add_payroll.html")



@app.route('/payroll_overview')
def payroll_overview():
    total_payroll = 0  # Initialize total payroll to zero

    # Fetch payroll records
    payroll_records = get_payroll_records()

    # Calculate total payroll
    if payroll_records:
        total_payroll = sum(record['salary_amount'] for record in payroll_records)

    return render_template('payroll_overview.html', total_payroll=total_payroll, payroll_records=payroll_records)



@app.route('/settings')
def settings():
    return render_template('settings.html')





if __name__ == '__main__':
    app.run(debug=True)
