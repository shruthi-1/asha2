import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google OAuth settings
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    
    # Firebase settings (for user data storage)
    FIREBASE_CREDENTIALS_PATH = "C:\\Users\\shrut\\OneDrive\\Desktop\\asha\\firebase\\firebase_cred.json"

    # Gemini API
    GEMINI_API_KEY = os.getenv("API_KEY")
    
    # App settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

