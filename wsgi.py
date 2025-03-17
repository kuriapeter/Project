import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from dotenv import load_dotenv
from app import app, db
from config import config
from waitress import serve
from models import User

# Load environment variables
load_dotenv()

# Use development config by default, override with FLASK_ENV
env = os.getenv('FLASK_ENV', 'development')
if env not in config:
    print(f"Error: Invalid environment '{env}'. Using 'development'.", file=sys.stderr)
    env = 'development'

# Load configuration
app.config.from_object(config[env])

def setup_logging():
    """Configure secure logging for the application"""
    # Create logs directory if it doesn't exist with secure permissions
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, mode=0o750)

    # Configure formatters with secure information
    app_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - '
        'Process:%(process)d - Thread:%(thread)d - '
        '%(message)s'
    )
    
    audit_formatter = logging.Formatter(
        '%(asctime)s - AUDIT - [%(levelname)s] - '
        'IP:%(remote_addr)s - User:%(user_id)s - '
        'Event:%(event_type)s - %(message)s'
    )
    
    security_formatter = logging.Formatter(
        '%(asctime)s - SECURITY - [%(levelname)s] - '
        'IP:%(remote_addr)s - User:%(user_id)s - '
        'Event:%(event_type)s - %(message)s - '
        'Additional:%(extra)s'
    )
    
    error_formatter = logging.Formatter(
        '%(asctime)s - ERROR - [%(levelname)s] - '
        'Process:%(process)d - Thread:%(thread)d - '
        '%(message)s\nTraceback: %(exc_info)s'
    )
    
    # Main application log
    app_log_file = os.path.join(log_dir, 'app.log')
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),  # 10MB
        backupCount=app.config.get('LOG_BACKUP_COUNT', 10),
        encoding='utf-8'
    )
    os.chmod(app_log_file, 0o640)  # Secure file permissions
    app_handler.setFormatter(app_formatter)
    app_handler.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
    
    # Audit log for security events
    audit_log_file = os.path.join(log_dir, 'audit.log')
    audit_handler = TimedRotatingFileHandler(
        audit_log_file,
        when='midnight',
        interval=1,
        backupCount=app.config.get('AUDIT_LOG_RETENTION_DAYS', 30),
        encoding='utf-8'
    )
    os.chmod(audit_log_file, 0o640)  # Secure file permissions
    audit_handler.setFormatter(audit_formatter)
    audit_handler.setLevel(logging.INFO)
    
    # Security incident log
    security_log_file = os.path.join(log_dir, 'security.log')
    security_handler = TimedRotatingFileHandler(
        security_log_file,
        when='midnight',
        interval=1,
        backupCount=app.config.get('SECURITY_LOG_RETENTION_DAYS', 90),
        encoding='utf-8'
    )
    os.chmod(security_log_file, 0o640)  # Secure file permissions
    security_handler.setFormatter(security_formatter)
    security_handler.setLevel(logging.INFO)
    
    # Error log
    error_log_file = os.path.join(log_dir, 'error.log')
    error_handler = TimedRotatingFileHandler(
        error_log_file,
        when='midnight',
        interval=1,
        backupCount=app.config.get('ERROR_LOG_RETENTION_DAYS', 30),
        encoding='utf-8'
    )
    os.chmod(error_log_file, 0o640)  # Secure file permissions
    error_handler.setFormatter(error_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Configure loggers
    app.logger.addHandler(app_handler)
    app.logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
    
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Prevent propagation
    
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False  # Prevent propagation
    
    error_logger = logging.getLogger('error')
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False  # Prevent propagation

def initialize_database():
    """Initialize the database and create admin user if not exists"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                name='Administrator',
                email='admin@company.com',
                username='admin',
                role='admin',
                department='Administration',
                position='System Administrator'
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Admin user created successfully")

def configure_production():
    """Configure production-specific settings"""
    if env == 'production':
        # Validate critical environment variables
        required_vars = ['SECRET_KEY', 'WTF_CSRF_SECRET_KEY', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}", 
                  file=sys.stderr)
            sys.exit(1)
        
        # Initialize database
        initialize_database()
        
        # Log startup
        app.logger.info("Application started in production mode")
        return True
    return False

if __name__ == "__main__":
    # Set up logging first
    setup_logging()
    
    # Initialize database in development mode
    if env == 'development':
        initialize_database()
        # Force development settings
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['REMEMBER_COOKIE_SECURE'] = False
    
    # Configure production if needed
    is_production = configure_production()
    
    if is_production:
        # Production settings for Waitress
        serve(app, 
              host='0.0.0.0',
              port=int(os.getenv('PORT', 8000)),
              threads=int(os.getenv('WAITRESS_THREADS', 4)),
              url_scheme='https',
              ident='Company Finance Tracker')
    else:
        # Development server
        app.run(
            host='127.0.0.1',
            port=int(os.getenv('PORT', 5000)),
            debug=True,
            ssl_context=None  # Force HTTP
        )
