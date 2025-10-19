# 🚀 RAILWAY DEPLOYMENT REHBERİ - Flask Chat v2.3

**GitHub Repository:** https://github.com/muhsinzengin/sohbet  
**Platform:** Railway Cloud  
**Plan:** Free ($5 kredi aylık)  
**Database:** PostgreSQL (otomatik)

---

## 📋 **RAILWAY'DA YAPMAN GEREKENLER**

### **1. Railway.com'a Git ve Login Ol**
- https://railway.app
- GitHub ile login ol
- "Start a New Project" butonuna tıkla

### **2. GitHub Repository Bağla**
- "Deploy from GitHub repo" seçeneğini tıkla
- `muhsinzengin/sohbet` repository'sini bul ve seç
- "Deploy" butonuna tıkla

### **3. Railway Otomatik Oluşturacak:**
- ✅ **Web Service** (Flask app)
- ✅ **PostgreSQL Database** (otomatik)
- ✅ **Environment Variables** (DATABASE_URL otomatik)

### **4. Environment Variables Ekle**
Railway Dashboard → Settings → Environment Variables:

```bash
# Core Application
SECRET_KEY=your-production-secret-key-32-chars-minimum
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# Database (Railway otomatik ekler)
DATABASE_URL=postgresql://username:password@host:port/database

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloudinary-name
CLOUDINARY_API_KEY=your-cloudinary-key
CLOUDINARY_API_SECRET=your-cloudinary-secret

# CORS
CORS_ORIGINS=https://your-app-name.railway.app
```

### **5. Deploy Tamamlandıktan Sonra:**
- **Ana Site:** `https://your-app-name.railway.app`
- **Test Dashboard:** `https://your-app-name.railway.app/test`
- **Admin Login:** `https://your-app-name.railway.app/login`
- **Health Check:** `https://your-app-name.railway.app/health`

---

## 🔧 **RAILWAY KONFİGÜRASYONU**

### **railway.json (Otomatik):**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app"
  }
}
```

### **requirements.txt (Güncel):**
```
Flask==3.0.0
Flask-SocketIO==5.3.5
python-dotenv==1.0.0
python-telegram-bot==21.0
cloudinary==1.36.0
gunicorn==21.2.0
eventlet==0.33.3
psycopg2-binary==2.9.9
cryptography==46.0.3
bleach==6.1.0
Flask-WTF==1.2.1
```

---

## 📊 **DEPLOYMENT SONRASI**

### **Test Et:**
```bash
# Health check
curl https://your-app-name.railway.app/health

# Test dashboard (admin login gerekli)
# https://your-app-name.railway.app/test
```

### **Logs Görüntüle:**
- Railway Dashboard → Deployments → Logs
- Real-time logs görüntüleyebilirsin

---

## 💰 **MALIYET**

**Free Plan:**
- **$5 kredi** aylık (yeterli)
- **512MB RAM**
- **1GB storage**
- **PostgreSQL database** dahil
- **HTTPS** otomatik
- **Custom domain** desteği

**Pro Plan (İsteğe bağlı):**
- **$20/month** (sınırsız)
- **Daha fazla RAM** ve storage
- **Priority support**

---

## ⚠️ **ÖNEMLİ NOTLAR**

1. **Database Connection:** PostgreSQL connection string'i Railway otomatik oluşturur
2. **Environment Variables:** Sensitive bilgileri Railway dashboard'da manuel ekle
3. **Auto-Deploy:** GitHub'a push yaptığında otomatik deploy olur
4. **Logs:** Railway dashboard'da real-time logs görüntüleyebilirsin
5. **HTTPS:** Otomatik SSL sertifikası
6. **Custom Domain:** İsteğe bağlı custom domain ekleyebilirsin

---

## 🎯 **DEPLOYMENT ADIMLARI ÖZET**

1. ✅ Railway.com'a git ve login ol
2. ✅ GitHub repository bağla
3. ✅ Environment variables ekle
4. ✅ Deploy et ve test et

**Toplam Süre:** 5-10 dakika  
**Maliyet:** $0/month (Free plan - $5 kredi)

**Railway deployment hazır!** 🚀✨
