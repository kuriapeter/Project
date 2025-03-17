from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, FloatField, TextAreaField, DateField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        ('employee', 'Employee'),
        ('hr', 'HR Manager'),
        ('finance', 'Finance Manager'),
        ('accountant', 'Accountant'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    department = StringField('Department', validators=[Length(max=50)])
    position = StringField('Position', validators=[Length(max=50)])
    submit = SubmitField('Register')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_password(self, field):
        password = field.data
        if not any(c.isupper() for c in password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not any(c.islower() for c in password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not any(c.isdigit() for c in password):
            raise ValidationError('Password must contain at least one number.')
        if not any(not c.isalnum() for c in password):
            raise ValidationError('Password must contain at least one special character.')

class UserEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('New Password', validators=[Length(min=8, message='Password must be at least 8 characters long')])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password', message='Passwords must match')])
    role = SelectField('Role', choices=[
        ('employee', 'Employee'),
        ('hr', 'HR Manager'),
        ('finance', 'Finance Manager'),
        ('accountant', 'Accountant'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    department = StringField('Department', validators=[Length(max=50)])
    position = StringField('Position', validators=[Length(max=50)])
    submit = SubmitField('Save Changes')

    def __init__(self, original_email, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if field.data != self.original_email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered. Please use a different email.')

    def validate_password(self, field):
        if field.data:  # Only validate if password is being changed
            password = field.data
            if not any(c.isupper() for c in password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            if not any(c.islower() for c in password):
                raise ValidationError('Password must contain at least one lowercase letter.')
            if not any(c.isdigit() for c in password):
                raise ValidationError('Password must contain at least one number.')
            if not any(not c.isalnum() for c in password):
                raise ValidationError('Password must contain at least one special character.')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8),
        EqualTo('password_confirm', message='Passwords must match')
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired()
    ])
    submit = SubmitField('Reset Password')

class TransactionForm(FlaskForm):
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Length(max=200)])
    category = SelectField('Category', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Submit')
