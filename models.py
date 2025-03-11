from sqlalchemy import Column, Integer, String, ForeignKey
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'user'  # Ensure table name is set

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128))
    incomes = db.relationship('Income', back_populates='user')
    expenses = db.relationship('Expense', back_populates='user')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

class Income(db.Model):
    __tablename__ = 'income'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    user = db.relationship("User", back_populates="incomes")

class Expense(db.Model):
    __tablename__ = 'expense'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    user = db.relationship("User", back_populates="expenses")
