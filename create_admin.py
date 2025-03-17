from flask import Flask
from models import db, User
from config import config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Use development config
    app.config.from_object(config['development'])
    
    # Override database URL if environment variable exists
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Construct URL from individual settings
        db_url = 'mysql://{}:{}@{}:{}/{}'.format(
            os.environ.get('DB_USER', 'root'),
            os.environ.get('DB_PASSWORD', ''),
            os.environ.get('DB_HOST', '127.0.0.1'),
            os.environ.get('DB_PORT', '3306'),
            os.environ.get('DB_NAME', 'company_finance')
        )
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    
    # Initialize extensions
    db.init_app(app)
    
    return app

def create_admin_user():
    """Create admin user if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Check if admin exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Create admin user
                admin = User(
                    username=os.environ.get('ADMIN_USERNAME', 'admin'),
                    email=os.environ.get('ADMIN_EMAIL', 'admin@company.com'),
                    role='admin'
                )
                # Using password from environment or default
                admin.set_password(os.environ.get('ADMIN_PASSWORD', 'AdminFinance@2025'))
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                print(f"Username: {admin.username}")
                print("Password: AdminFinance@2025 (if using default)")
            else:
                print("Admin user already exists!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")
            raise

if __name__ == '__main__':
    create_admin_user()
