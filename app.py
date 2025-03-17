from datetime import datetime, timedelta
import os
from flask import Flask, request, jsonify, g, abort, redirect, url_for, render_template, flash
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from models import db, User, Transaction, Budget, Payroll
from config import config

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='development'):
    # Create the application instance
    app = Flask(__name__)

    # Load config
    app.config.from_object(config[config_name])

    # Configure SQLAlchemy pool settings
    app.config['SQLALCHEMY_POOL_SIZE'] = 20
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 5
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800  # Recycle connections after 30 minutes

    # Override database URL if environment variable exists
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Construct URL from individual settings
        db_url = 'mysql://{}:{}@{}:{}/{}'.format(
            os.environ.get('DB_USER', 'root'),
            os.environ.get('DB_PASSWORD', ''),
            os.environ.get('DB_HOST', 'localhost'),
            os.environ.get('DB_PORT', '3306'),
            os.environ.get('DB_NAME', 'company_finance')
        )
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    # Force development settings for HTTP
    if config_name == 'development':
        app.config.update(
            SESSION_COOKIE_SECURE=False,
            REMEMBER_COOKIE_SECURE=False,
            SESSION_COOKIE_SAMESITE=None,
            REMEMBER_COOKIE_SAMESITE=None,
            SESSION_COOKIE_HTTPONLY=True,
            REMEMBER_COOKIE_HTTPONLY=True
        )

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID."""
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            app.logger.error(f"Error loading user {user_id}: {str(e)}")
            return None

    @app.before_request
    def before_request():
        """Log user activity and update last seen."""
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Failed to update user last seen: {str(e)}")
                db.session.rollback()

    # Role-based access control decorators
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_admin():
                abort(403)
            return f(*args, **kwargs)
        return decorated_function

    def finance_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_finance():
                abort(403)
            return f(*args, **kwargs)
        return decorated_function

    # Error handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({'error': 'Bad Request', 'message': str(error)}), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Please log in to access this resource'}), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource'}), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred'}), 500

    # Register blueprints
    from routes import auth_bp, main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Create database and admin user
    with app.app_context():
        try:
            db.create_all()
            
            # Create admin user if no users exist
            if not User.query.first():
                admin = User(
                    username='admin',
                    email='admin@company.com',
                    role='admin'
                )
                # Using a stronger password that meets all requirements:
                # - At least 12 characters
                # - Contains uppercase, lowercase, numbers, and special characters
                admin.set_password('AdminFinance@2025')
                db.session.add(admin)
                db.session.commit()
                app.logger.info('Created admin user successfully')
        except Exception as e:
            app.logger.error(f'Error during database initialization: {str(e)}')
            raise

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app

# Create the application instance
app = create_app('development')

if __name__ == '__main__':
    # Run in development mode with HTTP
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=False,
        ssl_context=None  # Force HTTP
    )
