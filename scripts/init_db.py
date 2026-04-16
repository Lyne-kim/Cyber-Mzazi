from dotenv import load_dotenv

load_dotenv()

from app import app
from webapp.extensions import db


with app.app_context():
    db.create_all()
    print("Database tables created successfully.")
