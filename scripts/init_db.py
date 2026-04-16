from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from app import app
from webapp.services.schema import ensure_runtime_schema


with app.app_context():
    ensure_runtime_schema()
    print("Database tables created successfully.")
