import re
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def validate_password(password):
    """
    Validate password complexity requirements:
    - Minimum length of 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets complexity requirements"

def admin_required(f):
    """Decorator to require admin role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role == 'admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def hr_required(f):
    """Decorator to require HR role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role == 'hr':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def finance_required(f):
    """Decorator to require finance role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role == 'finance':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles):
    """Decorator to require one of multiple roles for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.role in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('auth.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_password_reset_email(user, token):
    """Send a password reset email to the user."""
    reset_url = url_for('auth.reset_password_with_token', token=token, _external=True)
    
    # In a production environment, you would use a proper email service
    # For development, we'll just print the reset URL
    print(f"Password reset URL for {user.email}: {reset_url}")
    
    # Example of how to send email using Flask-Mail:
    # msg = Message('Password Reset Request',
    #               sender='noreply@example.com',
    #               recipients=[user.email])
    # msg.body = f'''To reset your password, visit the following link:
    # {reset_url}
    # If you did not make this request then simply ignore this email.
    # '''
    # mail.send(msg)
