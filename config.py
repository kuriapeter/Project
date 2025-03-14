class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://Sheriff:1234@localhost/finance_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your_secret_key'