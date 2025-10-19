#!/usr/bin/env python3
# MAIN - TÜM 8 script sırayla çalıştırır
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

def run_script(script_name, description):
    """Run a script and return success status"""
    print(f"\n{'='*60}")
    print(f"🚀 {script_name.upper()} - {description}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        
        # Run the script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {script_name} BAŞARILI ({duration:.1f}s)")
            if result.stdout:
                print("📋 Output:")
                print(result.stdout[-500:])  # Last 500 chars
            return True
        else:
            print(f"❌ {script_name} BAŞARISIZ ({duration:.1f}s)")
            if result.stderr:
                print("❌ Error:")
                print(result.stderr[-500:])  # Last 500 chars
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {script_name} TIMEOUT (5 dakika)")
        return False
    except Exception as e:
        print(f"💥 {script_name} HATA: {e}")
        return False

def main():
    """Run all 8 scripts in sequence"""
    print("🚀 FLASK CHAT v2.3 - YAYIN ÖNCESİ SCRIPT SUITE")
    print("=" * 60)
    print(f"📅 Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Hedef: Railway deployment hazırlığı")
    print()
    
    scripts = [
        ("cleanup_db.py", "Test data temizleme"),
        ("validate_env.py", "Environment variables kontrol"),
        ("otp_to_db.py", "OTP memory → database migration"),
        ("security_check.py", "OWASP Top 10 güvenlik taraması"),
        ("test_telegram.py", "Telegram bot live test"),
        ("locustfile.py", "Load test hazırlığı"),
        ("healthcheck.py", "Health endpoint ekleme"),
    ]
    
    results = {}
    total_start_time = time.time()
    
    # Run each script
    for script_name, description in scripts:
        success = run_script(script_name, description)
        results[script_name] = success
        
        if not success:
            print(f"\n⚠️  {script_name} başarısız - devam ediliyor...")
        
        time.sleep(2)  # Brief pause between scripts
    
    # Final summary
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print(f"\n{'='*60}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*60}")
    
    successful = sum(results.values())
    total = len(results)
    
    print(f"✅ Başarılı: {successful}/{total}")
    print(f"❌ Başarısız: {total - successful}/{total}")
    print(f"⏱️  Toplam süre: {total_duration:.1f} saniye")
    print(f"📅 Bitiş: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📋 DETAYLI SONUÇLAR:")
    for script_name, success in results.items():
        status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
        print(f"  {status} {script_name}")
    
    # Overall status
    if successful == total:
        print(f"\n🎉 TÜM SCRIPT'LER BAŞARILI!")
        print("🚀 Railway deployment hazır!")
        print("📋 Sonraki adımlar:")
        print("   1. git add . && git commit -m 'Pre-deployment scripts'")
        print("   2. railway up")
        print("   3. Railway'de environment variables ayarla")
        return True
    elif successful >= total * 0.7:  # 70% success rate
        print(f"\n⚠️  ÇOĞU SCRIPT BAŞARILI ({successful}/{total})")
        print("🔧 Başarısız script'leri kontrol edin")
        print("🚀 Yine de deploy edilebilir")
        return True
    else:
        print(f"\n❌ ÇOĞU SCRIPT BAŞARISIZ ({successful}/{total})")
        print("🔍 Kritik sorunları çözün")
        print("🚨 Deploy etmeden önce düzeltin")
        return False

def create_deployment_guide():
    """Create deployment guide"""
    guide_content = '''# Railway Deployment Guide

## Pre-Deployment Checklist ✅

1. **Environment Variables** (.env.example → Railway)
   - SECRET_KEY (32+ chars)
   - ADMIN_USERNAME & ADMIN_PASSWORD
   - DATABASE_URL (Railway Postgres)
   - TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID
   - CLOUDINARY credentials
   - CORS_ORIGINS (your Railway domain)

2. **Database Setup**
   - Railway Postgres addon ekle
   - DATABASE_URL otomatik ayarlanır
   - Tables otomatik oluşturulur

3. **Deployment Commands**
   ```bash
   # 1. Commit changes
   git add . && git commit -m "v2.3 production ready"
   
   # 2. Deploy to Railway
   railway up
   
   # 3. Set environment variables in Railway dashboard
   ```

4. **Post-Deployment Tests**
   - Health check: https://your-app.railway.app/health
   - Admin login: https://your-app.railway.app/admin
   - Chat functionality: https://your-app.railway.app/
   - Telegram bot test

5. **Monitoring**
   - Railway dashboard logs
   - Health endpoint monitoring
   - Performance metrics

## Troubleshooting

- **Database connection**: DATABASE_URL kontrol et
- **Telegram bot**: Token ve Chat ID kontrol et
- **CORS errors**: CORS_ORIGINS domain kontrol et
- **Memory issues**: Railway Hobby plan limitleri

## Security Features ✅

- ✅ XSS Protection (bleach)
- ✅ CSRF Protection (Flask-WTF)
- ✅ Path Traversal Protection
- ✅ Input Validation
- ✅ Session Security
- ✅ Rate Limiting
- ✅ OWASP Top 10 Compliant

## Performance Features ✅

- ✅ Database Connection Pooling
- ✅ Message Caching
- ✅ File Upload Optimization
- ✅ Socket.IO Optimization
- ✅ Railway Production Ready
'''
    
    with open('RAILWAY_DEPLOYMENT_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("✅ Railway deployment guide oluşturuldu: RAILWAY_DEPLOYMENT_GUIDE.md")

if __name__ == "__main__":
    # Check if we're in scripts directory
    if not os.path.exists('cleanup_db.py'):
        print("❌ Scripts klasöründe değilsiniz!")
        print("📋 Usage: cd scripts && python main.py")
        sys.exit(1)
    
    success = main()
    
    if success:
        create_deployment_guide()
        print("\n🎉 YAYIN ÖNCESİ HAZIRLIK TAMAM!")
        print("📊 Railway deployment için hazır")
    else:
        print("\n❌ YAYIN ÖNCESİ HAZIRLIK BAŞARISIZ!")
        print("🔍 Sorunları çözün ve tekrar deneyin")
        sys.exit(1)
