import os
from dotenv import load_dotenv

# Load environment variables (with error handling)
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Using default values...")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-must-be-32-chars-minimum-change-this-in-production')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    SQLITE_PATH = 'data/chat.db'
    
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    @staticmethod
    def is_production():
        return Config.DATABASE_URL and 'postgres' in Config.DATABASE_URL
    
    @staticmethod
    def validate_required_config():
        """Validate that all required configuration is present"""
        required_vars = ['SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD']
        missing = [var for var in required_vars if not getattr(Config, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return True
