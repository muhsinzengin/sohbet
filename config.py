import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
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
