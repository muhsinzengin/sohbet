#!/usr/bin/env python3
# CLEANUP_DB - Test users + old messages siler
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database import db
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_test_data():
    """Clean up test data from database"""
    print("🧹 CLEANUP BAŞLADI...")
    
    try:
        # Clean test users
        print("📝 Test kullanıcıları temizleniyor...")
        test_users_deleted = db.execute_query(
            "DELETE FROM users WHERE username LIKE '%test%' OR username LIKE '%demo%'"
        )
        print(f"✅ {test_users_deleted} test kullanıcısı silindi")
        
        # Clean old messages (older than 30 days)
        print("💬 Eski mesajlar temizleniyor...")
        cutoff_date = datetime.now() - timedelta(days=30)
        old_messages_deleted = db.execute_query(
            "DELETE FROM messages WHERE created_at < %s",
            (cutoff_date,)
        )
        print(f"✅ {old_messages_deleted} eski mesaj silindi")
        
        # Clean orphaned threads
        print("🧵 Orphaned thread'ler temizleniyor...")
        orphaned_threads = db.execute_query(
            """DELETE FROM threads WHERE id NOT IN (
                SELECT DISTINCT thread_id FROM messages WHERE thread_id IS NOT NULL
            )"""
        )
        print(f"✅ {orphaned_threads} orphaned thread silindi")
        
        # Clean telegram_links
        print("📱 Telegram link'leri temizleniyor...")
        telegram_links_deleted = db.execute_query(
            "DELETE FROM telegram_links WHERE created_at < %s",
            (cutoff_date,)
        )
        print(f"✅ {telegram_links_deleted} eski telegram link silindi")
        
        # Database optimization
        print("⚡ Database optimize ediliyor...")
        if Config.is_production():
            db.execute_query("VACUUM ANALYZE")
        else:
            db.execute_query("VACUUM")
        print("✅ Database optimize edildi")
        
        print("🎉 CLEANUP TAMAM!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup hatası: {e}")
        print(f"❌ HATA: {e}")
        return False

if __name__ == "__main__":
    print("🚀 DATABASE CLEANUP SCRIPT")
    print("=" * 50)
    
    success = cleanup_test_data()
    
    if success:
        print("\n✅ CLEANUP BAŞARILI!")
        print("📊 Database temiz ve optimize edildi")
    else:
        print("\n❌ CLEANUP BAŞARISIZ!")
        print("🔍 Logları kontrol edin")
        sys.exit(1)
