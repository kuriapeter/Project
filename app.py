from flask import Flask, redirect, url_for
from config import Config
from extensions import db, login_manager
from routes import auth_bp
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))  # Use User.query.get() for clarity

    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    return app

app = create_app()

with app.app_context():
    db.create_all()  # Ensure all models are created

if __name__ == '__main__':
    app.run(debug=True)
