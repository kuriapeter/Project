import os
from datetime import timedelta

class Config:
    # Security settings - ensure SECRET_KEY is required
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set in environment variables")
    
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY')
    if not WTF_CSRF_SECRET_KEY:
        raise ValueError("No WTF_CSRF_SECRET_KEY set in environment variables")
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        # Construct URL from individual settings for XAMPP
        SQLALCHEMY_DATABASE_URI = 'mysql://{}:{}@{}:{}/{}'.format(
            os.environ.get('DB_USER', 'root'),
            os.environ.get('DB_PASSWORD', ''),
            os.environ.get('DB_HOST', '127.0.0.1'),  # Use 127.0.0.1 for XAMPP
            os.environ.get('DB_PORT', '3306'),
            os.environ.get('DB_NAME', 'company_finance')
        )
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'True').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True  # Enable automatic reconnection
    }
    
    # Session settings with stronger defaults
    try:
        session_lifetime = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '30').strip())
    except (ValueError, TypeError):
        session_lifetime = 30
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=session_lifetime)
    
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_TYPE = 'redis'
    
    # Flask-Login settings with stronger security
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'True').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    try:
        remember_duration = int(os.environ.get('REMEMBER_COOKIE_DURATION', '14').strip())
    except (ValueError, TypeError):
        remember_duration = 14
    REMEMBER_COOKIE_DURATION = timedelta(days=remember_duration)
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Rate limiting settings
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', "200 per day;50 per hour")
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    @classmethod
    def init_app(cls, app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    
    # Explicitly disable HTTPS requirements in development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = None
    REMEMBER_COOKIE_SAMESITE = None
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Force development settings
        app.config.update(
            SESSION_COOKIE_SECURE=False,
            REMEMBER_COOKIE_SECURE=False,
            SESSION_COOKIE_SAMESITE=None,
            REMEMBER_COOKIE_SAMESITE=None
        )
        app.logger.warning('Running in development mode - security features are relaxed')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # Enforce security in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production checks
        if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
            raise ValueError("Production requires a strong SECRET_KEY")
            
        if not app.config['WTF_CSRF_SECRET_KEY']:
            raise ValueError("Production requires WTF_CSRF_SECRET_KEY")
            
        if not app.config.get('MAIL_SERVER'):
            raise ValueError("Production requires mail server configuration")
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}