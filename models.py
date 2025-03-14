def get_financial_overview(mysql):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT SUM(amount) AS total_income FROM transactions WHERE type='income'")
        total_income = cursor.fetchone()["total_income"] or 0

        cursor.execute("SELECT SUM(amount) AS total_expense FROM transactions WHERE type='expense'")
        total_expense = cursor.fetchone()["total_expense"] or 0

        net_profit = total_income - total_expense

        cursor.close()

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit
        }
    except Exception as e:
        print("Database Error:", str(e))
        return {"error": str(e)}

def add_transaction(mysql, trans_type, amount, description, date):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO transactions (type, amount, description, date) VALUES (%s, %s, %s, %s)",
        (trans_type, amount, description, date)
    )
    mysql.connection.commit()
    cur.close()



from flask_mysqldb import MySQL

import MySQLdb.cursors  # Import MySQLdb cursors

def get_monthly_income_expenses(mysql):
    """Fetch total income and expenses for each month."""
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor

    cur.execute("""
        SELECT 
            DATE_FORMAT(date, '%Y-%m') AS month, 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        GROUP BY month
        ORDER BY month
    """)

    data = cur.fetchall()  # Fetch all rows
    cur.close()

    print("DEBUG: MySQL Query Result:", data)  # Debugging line

    # Convert dictionary data
    return [{"month": row["month"], "income": row["total_income"] or 0, "expense": row["total_expense"] or 0} for row in data]


import MySQLdb.cursors  # Import DictCursor

def get_expense_breakdown(mysql):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  
    cursor.execute("SELECT category, SUM(amount) AS total FROM transactions WHERE type = 'expense' GROUP BY category")
    data = cursor.fetchall()
    cursor.close()

    print("Expense breakdown data:", data)  # Debugging output

    return [{"category": row["category"], "total": float(row["total"])} for row in data]



def get_top_spending_categories(mysql):
    try:
        connection = mysql.connect()
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor

        query = """
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
        LIMIT 5
        """
        cursor.execute(query)
        data = cursor.fetchall()  # Fetch as list of dictionaries

        cursor.close()
        connection.close()

        return [{"category": row["category"], "total": float(row["total"])} for row in data]

    except Exception as e:
        print("Error fetching top spending categories:", e)
        return []

# Add or Update Budget
def set_budget(mysql, category, amount):
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO budgets (category, budget_amount) 
        VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE budget_amount = %s
    """, (category, amount, amount))  # Pass amount again for update
    mysql.connection.commit()
    cur.close()


# Get All Budgets
def get_budgets(mysql):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM budgets")
    data = cur.fetchall()
    cur.close()
    return data

# Get Spending by Category
def get_spending_by_category(mysql):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT category, SUM(amount) as spent 
        FROM transactions 
        
        GROUP BY category
    """)
    data = cur.fetchall()
    cur.close()
    return data


# models.py


def get_recent_transactions(mysql):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT date, category, amount, status FROM transactions ORDER BY date DESC LIMIT 10")
        data = cursor.fetchall()
        cursor.close()

        if not data:  # ✅ Return empty list if no data
            return []

        return [
            {
                "date": str(row[0]),
                "category": row[1],
                "amount": float(row[2]),
                "status": row[3]
            }
            for row in data
        ]
    except Exception as e:
        print("Error:", str(e))
        return []

def get_kpi_data(mysql):
    conn = mysql.connection.cursor()
    conn.execute("SELECT SUM(income) FROM transactions")  
    result = conn.fetchone()
    
    total_income = result.get(0, 0) if isinstance(result, dict) else (result[0] if result else 0)

    return {"total_income": total_income}

def get_yearly_income_expenses(mysql):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                YEAR(date) AS year, 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expenses
            FROM transactions
            GROUP BY YEAR(date)
            ORDER BY YEAR(date) ASC
        """)
        data = cur.fetchall()
        cur.close()
        return [{"year": row[0], "income": row[1], "expenses": row[2]} for row in data]
    except Exception as e:
        return {"error": str(e)}

def get_alerts(mysql):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM alerts")
    alerts = cursor.fetchall()
    cursor.close()
    return alerts

def get_payroll_records():
    # Query all payroll records from the database
    records = Payroll.query.all()
    return [{
        'name': record.employee_name,
        'salary_amount': record.salary_amount,
        'pay_date': record.pay_date.strftime('%Y-%m-%d'),  # Format date as needed
        'status': record.status
    } for record in records]
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Payroll(db.Model):
    __tablename__ = 'payroll'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False)
    salary_amount = db.Column(db.Float, nullable=False)
    pay_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Payroll {self.employee_id}, Amount: {self.salary_amount}, Date: {self.pay_date}>'
