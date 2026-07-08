import sys
import os

# Add backend directory to python path so imports in backend/app work correctly
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Import the FastAPI app instance from backend/app/main.py
from app.main import app
