class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/finance_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your_secret_key'  # Change this to a random secret key
