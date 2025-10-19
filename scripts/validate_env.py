#!/usr/bin/env python3
# VALIDATE_ENV - Railway ENV vars kontrol eder
import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_environment():
    """Validate all required environment variables"""
    print("🔍 ENV VALIDATION BAŞLADI...")
    
    required_vars = {
        'SECRET_KEY': 'Flask secret key (32+ chars)',
        'ADMIN_USERNAME': 'Admin kullanıcı adı',
        'ADMIN_PASSWORD': 'Admin şifresi',
        'DATABASE_URL': 'PostgreSQL connection string',
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token',
        'TELEGRAM_CHAT_ID': 'Telegram chat ID',
        'CLOUDINARY_CLOUD_NAME': 'Cloudinary cloud name',
        'CLOUDINARY_API_KEY': 'Cloudinary API key',
        'CLOUDINARY_API_SECRET': 'Cloudinary API secret'
    }
    
    optional_vars = {
        'PORT': 'Server port (Railway auto-sets)',
        'CORS_ORIGINS': 'CORS allowed origins',
        'FLASK_ENV': 'Flask environment'
    }
    
    missing_vars = []
    invalid_vars = []
    
    print("📋 Required variables kontrol ediliyor...")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: MISSING - {description}")
        else:
            # Basic validation
            if var == 'SECRET_KEY' and len(value) < 32:
                invalid_vars.append(f"{var} (too short)")
                print(f"⚠️  {var}: TOO SHORT (min 32 chars)")
            elif var == 'DATABASE_URL' and 'postgres' not in value.lower():
                invalid_vars.append(f"{var} (not PostgreSQL)")
                print(f"⚠️  {var}: NOT POSTGRESQL")
            else:
                print(f"✅ {var}: OK")
    
    print("\n📋 Optional variables kontrol ediliyor...")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"ℹ️  {var}: NOT SET - {description}")
    
    # Test database connection
    print("\n🔗 Database connection test ediliyor...")
    try:
        Config.validate_required_config()
        print("✅ Config validation: OK")
        
        # Test database connection
        from database import db
        result = db.execute_query("SELECT 1 as test")
        if result:
            print("✅ Database connection: OK")
        else:
            print("❌ Database connection: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Database test hatası: {e}")
        return False
    
    # Test Telegram bot
    print("\n🤖 Telegram bot test ediliyor...")
    try:
        import requests
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if bot_token:
            response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Telegram bot: {bot_info['result']['first_name']}")
            else:
                print(f"❌ Telegram bot: INVALID TOKEN")
                return False
        else:
            print("❌ Telegram bot: NO TOKEN")
            return False
    except Exception as e:
        print(f"❌ Telegram test hatası: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 50)
    if missing_vars or invalid_vars:
        print("❌ VALIDATION BAŞARISIZ!")
        if missing_vars:
            print(f"Missing: {', '.join(missing_vars)}")
        if invalid_vars:
            print(f"Invalid: {', '.join(invalid_vars)}")
        return False
    else:
        print("✅ VALIDATION BAŞARILI!")
        print("🚀 Railway deployment hazır!")
        return True

if __name__ == "__main__":
    print("🚀 ENVIRONMENT VALIDATION SCRIPT")
    print("=" * 50)
    
    success = validate_environment()
    
    if success:
        print("\n🎉 TÜM ENV VARS OK!")
        print("📊 Railway'e deploy edilebilir")
    else:
        print("\n❌ ENV VARS EKSIK!")
        print("🔍 .env.example dosyasını kontrol edin")
        sys.exit(1)
