# 🚀 RENDER.COM DEPLOYMENT REHBERİ - Flask Chat v2.3

**GitHub Repository:** https://github.com/muhsinzengin/sohbet  
**Template:** Web Service + PostgreSQL Database  
**Plan:** Starter ($7/month each = $14/month total)

---

## 📋 **RENDER'DA YAPMAN GEREKENLER**

### **1. Render.com'a Git ve Login Ol**
- https://render.com
- GitHub ile login ol
- "New +" butonuna tıkla

### **2. Web Service Oluştur**
- **Service Type:** `Web Service`
- **Name:** `flask-chat-app`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
- **Plan:** `Starter` ($7/month)

### **3. PostgreSQL Database Oluştur**
- **Service Type:** `PostgreSQL`
- **Name:** `flask-chat-db`
- **Plan:** `Starter` ($7/month)
- **Database Name:** `flask_chat`
- **User:** `flask_chat_user`

### **4. Environment Variables Ayarla**

**Web Service'de şu environment variables'ları ekle:**

```bash
# Core Application
SECRET_KEY=your-production-secret-key-32-chars-minimum
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# Database (Render otomatik ekler)
DATABASE_URL=postgresql://flask_chat_user:password@host:port/flask_chat

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloudinary-name
CLOUDINARY_API_KEY=your-cloudinary-key
CLOUDINARY_API_SECRET=your-cloudinary-secret
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# CORS
CORS_ORIGINS=https://flask-chat-app.onrender.com
```

### **5. GitHub Repository Bağla**
- **Repository:** `muhsinzengin/sohbet`
- **Branch:** `master`
- **Root Directory:** `/` (boş bırak)
- **Auto-Deploy:** `Yes`

### **6. Health Check Ayarla**
- **Health Check Path:** `/health`
- **Health Check Timeout:** `300 seconds`

---

## 🔧 **RENDER YAML KULLANIMI (OPSIYONEL)**

Eğer `render.yaml` dosyasını kullanmak istersen:

1. **Repository'ye render.yaml ekle** (zaten eklendi)
2. **Render Dashboard'da:**
   - "New +" → "Blueprint"
   - GitHub repository'yi seç
   - "Apply" butonuna tıkla
   - Otomatik olarak Web Service + Database oluşturacak

---

## 📊 **DEPLOYMENT SONRASI**

### **URL'ler:**
- **Ana Site:** `https://flask-chat-app.onrender.com`
- **Test Dashboard:** `https://flask-chat-app.onrender.com/test`
- **Admin Login:** `https://flask-chat-app.onrender.com/login`
- **Health Check:** `https://flask-chat-app.onrender.com/health`

### **Test Et:**
```bash
# Health check
curl https://flask-chat-app.onrender.com/health

# Test dashboard (admin login gerekli)
# https://flask-chat-app.onrender.com/test
```

---

## 💰 **MALIYET**

**Starter Plan:**
- **Web Service:** $7/month (512MB RAM)
- **PostgreSQL:** $7/month (1GB storage)
- **Toplam:** $14/month

**Free Plan (Test için):**
- Web Service: 750 saat/ay (yaklaşık 30 gün)
- PostgreSQL: 1GB storage
- **Uyarı:** Free plan'da uygulama 15 dakika idle sonra sleep'e geçer

---

## ⚠️ **ÖNEMLİ NOTLAR**

1. **Cold Start:** Free plan'da 15 dakika idle sonra uygulama sleep'e geçer
2. **Database Connection:** PostgreSQL connection string'i Render otomatik oluşturur
3. **Environment Variables:** Sensitive bilgileri Render dashboard'da manuel ekle
4. **Auto-Deploy:** GitHub'a push yaptığında otomatik deploy olur
5. **Logs:** Render dashboard'da real-time logs görüntüleyebilirsin

---

## 🎯 **DEPLOYMENT ADIMLARI ÖZET**

1. ✅ Render.com'a git ve login ol
2. ✅ Web Service oluştur (Python 3)
3. ✅ PostgreSQL Database oluştur
4. ✅ Environment variables ekle
5. ✅ GitHub repository bağla
6. ✅ Deploy et ve test et

**Toplam Süre:** 10-15 dakika  
**Maliyet:** $14/month (Starter plan)

**Render deployment hazır!** 🚀✨
