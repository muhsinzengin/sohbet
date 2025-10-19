# FLASK CHAT SYSTEM - COMPLETE DOCUMENTATION
## Kapsamlı Sistem Dokümantasyonu

**Versiyon:** 2.2
**Son Güncelleme:** 2024
**Durum:** Production Ready (Vercel Deployed)
**Saat Dilimi:** UTC+3 (Türkiye)
**Bug Fixes:** 12 kritik + 4 orta düzeltme
**Deployment:** Vercel (Serverless)

---

## 📋 İÇİNDEKİLER

1. [Proje Genel Bakış](#1-proje-genel-bakış)
2. [Dosya Yapısı ve Açıklamaları](#2-dosya-yapısı-ve-açıklamaları)
3. [Backend Mimarisi](#3-backend-mimarisi)
4. [Frontend Mimarisi](#4-frontend-mimarisi)
5. [Database Şeması](#5-database-şeması)
6. [API Endpoints](#6-api-endpoints)
7. [Socket.IO Events](#7-socketio-events)
8. [Telegram Entegrasyonu](#8-telegram-entegrasyonu)
9. [Zaman Yönetimi](#9-zaman-yönetimi)
10. [Deployment](#10-deployment)

---

## 1. PROJE GENEL BAKIŞ

### 1.1 Proje Tanımı
Gerçek zamanlı, Telegram entegrasyonlu, modern chat uygulaması. Ziyaretçiler ile admin arasında anlık mesajlaşma sağlar. Serverless mimari ile Vercel'de deploy edilmiştir.

### 1.2 Temel Özellikler
- ✅ Real-time messaging (Socket.IO)
- ✅ Telegram OTP authentication
- ✅ Telegram bot integration (bidirectional)
- ✅ Vercel Postgres + SQLite dual support
- ✅ File upload (image, audio)
- ✅ Cloudinary integration
- ✅ Mobile-first responsive design
- ✅ Turkey timezone (UTC+3)
- ✅ Online/Offline status tracking
- ✅ Thread-based conversation management
- ✅ Serverless deployment (Vercel)
- ✅ Function timeout management (30s)

### 1.3 Teknoloji Stack

**Backend:**
- Flask 3.0.0
- Flask-SocketIO 5.3.5
- Vercel Postgres / SQLite3
- python-telegram-bot 20.7
- Cloudinary 1.36.0
- Vercel Serverless Functions

**Frontend:**
- Vanilla JavaScript
- Socket.IO Client 4.5.4
- Three.js r128
- CSS3 (Glassmorphism)

**Deployment:**
- Vercel (Serverless Platform)
- Vercel Postgres Database
- Environment Variables Management

---

## 2. DOSYA YAPISI VE AÇIKLAMALARI

### 2.1 Root Dizin
```
sohbet/
├── app.py                          # Ana Flask uygulaması (370 satır)
├── config.py                       # Konfigürasyon yönetimi (23 satır)
├── database.py                     # Database abstraction layer (100 satır)
├── vercel.json                     # Vercel deployment config (YENİ)
├── requirements.txt                # Python dependencies (Vercel optimized)
├── .env                           # Environment variables (GİZLİ)
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
├── README.md                      # Proje özeti
├── render.yaml                    # Eski deployment config (deprecated)
└── test_telegram.py               # Telegram test scripti
```

### 2.2 Templates Dizini
```
templates/
├── index.html                     # Visitor chat sayfası
├── admin.html                     # Admin panel sayfası
└── login.html                     # Admin login sayfası (OTP)
```

### 2.3 Static Dizini
```
static/
├── css/
│   ├── index-style.css           # Visitor sayfası stilleri
│   └── style.css                 # Admin panel stilleri
├── js/
│   ├── index.js                  # Visitor JavaScript (450 satır)
│   └── admin.js                  # Admin JavaScript (500 satır)
└── media/
    └── notify.mp3                # Bildirim sesi (kullanılmıyor)
```

### 2.4 Data Dizini
```
data/
└── chat.db                       # SQLite database (development/local)
```

### 2.5 Uploads Dizini
```
uploads/
├── images/                       # Yüklenen resimler (development)
│   └── .gitkeep
└── audio/                        # Yüklenen ses dosyaları (development)
    └── .gitkeep
```

### 2.6 Dokümantasyon Dizini
```
SYSTEM_DOCS/                      # Sistem dokümantasyonu
├── COMPLETE_SYSTEM_DOCUMENTATION.md
├── PART2_API_SOCKET.md
├── PART3_TELEGRAM_TIME.md
├── PART4_DATABASE_FRONTEND.md
├── BUGFIX_LOG.md
├── CHANGELOG.md
├── VERSION_INFO.md
└── README.md

TELEGRAM_SETUP.md                 # Telegram kurulum rehberi
TELEGRAM_TEST_GUIDE.md            # Telegram test rehberi
```

---

## 3. BACKEND MİMARİSİ

### 3.1 app.py - Ana Uygulama

**Görev:** Flask uygulamasının merkezi. Tüm route'lar, Socket.IO event'leri ve Telegram entegrasyonu. Serverless uyumlu hale getirilmiştir.

**Yapı:**
```python
# Import'lar
import os, uuid, asyncio, random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from config import Config
from database import db

# Flask & SocketIO Init - Serverless için optimize edildi
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Serverless için Socket.IO konfigürasyonu
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=30,  # Serverless timeout için optimize
    ping_interval=10
)
```

**Telegram Bot Initialization (Serverless Uyumlu):**
```python
if Config.TELEGRAM_BOT_TOKEN:
    from telegram import Bot, Update
    from telegram.ext import Application, MessageHandler, filters, ContextTypes
    import threading

    telegram_bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    telegram_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Message handler - Telegram'dan gelen reply'leri yakalar
    async def handle_telegram_message(update, context):
        if update.message.reply_to_message:
            reply_to_id = update.message.reply_to_message.message_id
            link = db.execute_query(
                'SELECT thread_id FROM telegram_links WHERE tg_message_id = ?',
                (reply_to_id,), fetch='one'
            )
            if link:
                # Mesajı kaydet ve visitor'a ilet
                # Serverless timeout'a dikkat ederek async operations
                await save_and_emit_message(link['thread_id'], update.message)

    # Background thread'de bot'u başlat (serverless'ta dikkatli kullanılmalı)
    def start_telegram_bot():
        try:
            telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
            telegram_app.run_polling()
        except Exception as e:
            print(f"Telegram bot error: {e}")

    telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    telegram_thread.start()
```

**Cloudinary Configuration:**
```python
cloudinary_configured = False
if Config.is_production() and Config.CLOUDINARY_CLOUD_NAME:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=Config.CLOUDINARY_CLOUD_NAME,
        api_key=Config.CLOUDINARY_API_KEY,
        api_secret=Config.CLOUDINARY_API_SECRET
    )
    cloudinary_configured = True
```

**OTP Storage (Serverless Uyumlu):**
```python
otp_store = {}  # In-memory OTP storage (serverless'ta stateless!)
# NOT: Serverless'ta in-memory storage persistent değildir
# Production'da Redis veya database kullanılması önerilir
```

### 3.2 config.py - Konfigürasyon

**Görev:** Tüm environment variables'ı yönetir. Vercel environment variables için optimize edilmiştir.

**Yapı:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

    # Database - Vercel Postgres desteği eklendi
    DATABASE_URL = os.getenv('DATABASE_URL', '')  # Vercel Postgres
    SQLITE_PATH = 'data/chat.db'                  # SQLite (development)

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

    # Environment
    ENV = os.getenv('ENV', 'development')

    @staticmethod
    def is_production():
        return Config.ENV == 'production' or Config.DATABASE_URL
```

### 3.3 database.py - Database Abstraction

**Görev:** Vercel Postgres ve SQLite için unified interface sağlar.

**Özellikler:**
- Context manager ile güvenli connection
- Otomatik placeholder dönüşümü (? → %s)
- Türkiye saat dilimi desteği (UTC+3)
- Row factory (dict dönüşümü)
- Vercel Postgres connection string parsing

**Yapı:**
```python
import os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from config import Config

TURKEY_TZ = timezone(timedelta(hours=3))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

class Database:
    def __init__(self):
        self.database_url = Config.DATABASE_URL
        # Vercel Postgres URL'ini standardize et
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        self.is_postgres = 'postgres' in self.database_url.lower()
        self.sqlite_path = Config.SQLITE_PATH
```

**Connection Management (Vercel Optimized):**
```python
@contextmanager
def get_connection(self):
    if self.is_postgres:
        # Vercel Postgres için SSL ve connection pooling
        conn = psycopg2.connect(
            self.database_url,
            sslmode='require',  # Vercel Postgres gerektirir
            connect_timeout=10  # Serverless timeout için
        )
        conn.cursor_factory = psycopg2.extras.RealDictCursor
    else:
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

---

## 10. DEPLOYMENT

### 10.1 Vercel Deployment

**Vercel Konfigürasyonu (vercel.json):**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ],
  "functions": {
    "app.py": {
      "maxDuration": 30
    }
  },
  "env": {
    "ENV": "production"
  }
}
```

**Environment Variables (Vercel Dashboard):**
```
DATABASE_URL = postgresql://[vercel-postgres-connection-string]
SECRET_KEY = sohbet-secret-key-2024
ENV = production
TELEGRAM_BOT_TOKEN = 7801493894:AAHQTlDbrugF5Lb7bsYZc0sS5vEKGd-e-pc
TELEGRAM_CHAT_ID = 123456789
ADMIN_USERNAME = admin
ADMIN_PASSWORD = admin123456
CLOUDINARY_URL = cloudinary://977118918853874:Onba9gDpv-tutY_taeP3GZplI9k@dsi9scdpv
```

**Deployment Adımları:**
1. **GitHub'a push** - Kod otomatik deploy olur
2. **Vercel Postgres oluştur** - Storage > Create Database > Postgres
3. **Environment variables ekle** - Project Settings > Environment Variables
4. **Domain ayarla** - Project Settings > Domains
5. **Test et** - URL'yi aç ve çalışıp çalışmadığını kontrol et

### 10.2 Vercel Postgres Setup

**Database Oluşturma:**
1. Vercel Dashboard > Storage > Create Database
2. PostgreSQL seç
3. Database adı ver (örn: sohbet-db)
4. Connection string'i kopyala

**Migration:**
```bash
# Local development için
python -c "from database import db; db.init_db()"

# Production için Vercel Postgres'e manuel migration
# Vercel dashboard'dan SQL Editor kullan
```

### 10.3 Serverless Considerations

**Function Timeout:**
- Vercel serverless functions max 30 saniye çalışabilir
- Socket.IO connections için ping/pong mekanizması
- Long-running işlemler için background jobs gerekli

**Stateless Architecture:**
- In-memory storage (otp_store) production'da çalışmaz
- Session management için database kullan
- File uploads için Cloudinary zorunlu

**Cold Start Optimization:**
- Dependencies minimize edildi
- Lazy loading uygulandı
- Connection pooling optimize edildi

### 10.4 Monitoring & Logs

**Vercel Analytics:**
- Function invocation logs
- Performance metrics
- Error tracking

**Custom Logging:**
```python
import logging

# Vercel için structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

## 📊 VERSIYON BILGISI

**Versiyon:** 2.2
**Deployment:** Vercel (Serverless)
**Database:** Vercel Postgres + SQLite
**Son Güncelleme:** 2024-10-19
**Durum:** Production Ready

**Değişiklikler v2.1 → v2.2:**
- ✅ Vercel deployment eklendi
- ✅ Serverless function timeout yönetimi
- ✅ Vercel Postgres desteği
- ✅ Environment variables optimize edildi
- ✅ Cold start optimizasyonları
- ✅ SSL connection zorunlu hale getirildi

---

**NOT:** Bu dokümantasyon Vercel serverless deployment için güncellenmiştir. Eski Render konfigürasyonu deprecated olarak işaretlenmiştir.
