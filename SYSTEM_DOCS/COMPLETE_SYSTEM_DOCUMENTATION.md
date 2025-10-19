# FLASK CHAT SYSTEM - COMPLETE DOCUMENTATION
## Kapsamlı Sistem Dokümantasyonu

**Versiyon:** 2.1  
**Son Güncelleme:** 2024  
**Durum:** Production Ready (Bug Fixed)  
**Saat Dilimi:** UTC+3 (Türkiye)  
**Bug Fixes:** 12 kritik + 4 orta düzeltme

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
Gerçek zamanlı, Telegram entegrasyonlu, modern chat uygulaması. Ziyaretçiler ile admin arasında anlık mesajlaşma sağlar.

### 1.2 Temel Özellikler
- ✅ Real-time messaging (Socket.IO)
- ✅ Telegram OTP authentication
- ✅ Telegram bot integration (bidirectional)
- ✅ SQLite/PostgreSQL dual support
- ✅ File upload (image, audio)
- ✅ Cloudinary integration
- ✅ Mobile-first responsive design
- ✅ Turkey timezone (UTC+3)
- ✅ Online/Offline status tracking
- ✅ Thread-based conversation management

### 1.3 Teknoloji Stack

**Backend:**
- Flask 3.0.0
- Flask-SocketIO 5.3.5
- SQLite3 / PostgreSQL
- python-telegram-bot 20.7
- Cloudinary 1.36.0

**Frontend:**
- Vanilla JavaScript
- Socket.IO Client 4.5.4
- Three.js r128
- CSS3 (Glassmorphism)

**Deployment:**
- Gunicorn + Eventlet
- Render (Cloud Platform)

---

## 2. DOSYA YAPISI VE AÇIKLAMALARI

### 2.1 Root Dizin
```
sohbet/
├── app.py                          # Ana Flask uygulaması (370 satır)
├── config.py                       # Konfigürasyon yönetimi (23 satır)
├── database.py                     # Database abstraction layer (100 satır)
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (GİZLİ)
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
├── README.md                      # Proje özeti
├── render.yaml                    # Render deployment config
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
└── chat.db                       # SQLite database (development)
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
hazırlık/                         # Referans dokümantasyonu
├── PROJE_DOKUMANTASYONU.md
├── KURULUM_DOKUMANTASYONU.md
├── FRONTEND_DOKUMANTASYONU.md
├── CSS_DOKUMANTASYONU.md
└── ADMIN_JS_DOKUMANTASYONU.md

SYSTEM_DOCS/                      # Sistem dokümantasyonu (BU KLASÖR)
└── COMPLETE_SYSTEM_DOCUMENTATION.md

TELEGRAM_SETUP.md                 # Telegram kurulum rehberi
TELEGRAM_TEST_GUIDE.md            # Telegram test rehberi
```

---

## 3. BACKEND MİMARİSİ

### 3.1 app.py - Ana Uygulama

**Görev:** Flask uygulamasının merkezi. Tüm route'lar, Socket.IO event'leri ve Telegram entegrasyonu.

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

# Flask & SocketIO Init
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
```

**Telegram Bot Initialization:**
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
                ...
    
    # Background thread'de bot'u başlat
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

**OTP Storage:**
```python
otp_store = {}  # In-memory OTP storage
# Format: {'admin': {'code': '123456', 'expires': datetime}}
```

### 3.2 config.py - Konfigürasyon

**Görev:** Tüm environment variables'ı yönetir.

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
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', '')  # PostgreSQL
    SQLITE_PATH = 'data/chat.db'                  # SQLite
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    @staticmethod
    def is_production():
        return Config.DATABASE_URL and 'postgres' in Config.DATABASE_URL
```

**Kullanım:**
```python
from config import Config

if Config.is_production():
    # Production logic
else:
    # Development logic
```

### 3.3 database.py - Database Abstraction

**Görev:** SQLite ve PostgreSQL için unified interface sağlar.

**Özellikler:**
- Context manager ile güvenli connection
- Otomatik placeholder dönüşümü (? → %s)
- Türkiye saat dilimi desteği (UTC+3)
- Row factory (dict dönüşümü)

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
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        self.is_postgres = 'postgres' in self.database_url.lower()
        self.sqlite_path = Config.SQLITE_PATH
```

**Connection Management:**
```python
@contextmanager
def get_connection(self):
    if self.is_postgres:
        conn = psycopg2.connect(self.database_url)
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

**Query Execution:**
```python
def execute_query(self, query, params=(), fetch='all'):
    # PostgreSQL için placeholder dönüşümü
    query = query.replace('?', '%s') if self.is_postgres else query
    
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == 'one':
            result = cursor.fetchone()
            return dict(result) if result else None
        elif fetch == 'all':
            return [dict(row) for row in cursor.fetchall()]
        else:
            conn.commit()
            return None
```

**Database Initialization:**
```python
def init_db(self):
    schema = '''
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours')),
        last_activity_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
    );
    
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        type TEXT NOT NULL,
        content_text TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours')),
        FOREIGN KEY (thread_id) REFERENCES threads(id)
    );
    
    CREATE TABLE IF NOT EXISTS telegram_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  # SQLite
        # id SERIAL PRIMARY KEY,                # PostgreSQL
        thread_id TEXT NOT NULL,
        tg_chat_id TEXT NOT NULL,
        tg_message_id INTEGER NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES threads(id)
    );
    '''
```

---

