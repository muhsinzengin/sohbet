# Flask Chat Uygulaması v2.3

Modern, gerçek zamanlı chat uygulaması - Telegram OTP entegrasyonlu + Enterprise Test Dashboard

## Özellikler

- ✅ Gerçek zamanlı mesajlaşma (Socket.IO)
- ✅ Telegram OTP ile güvenli admin girişi
- ✅ SQLite/PostgreSQL dual support
- ✅ Dosya yükleme (resim, ses)
- ✅ Cloudinary entegrasyonu
- ✅ Mobile-first responsive tasarım
- ✅ Railway/Render/Vercel deployment ready
- ✅ XSS koruması ve rate limiting
- ✅ Cache sistemi ile performans optimizasyonu
- ✅ **Enterprise Test Dashboard (120 test + 50 auto-fix)**

## Kurulum

```bash
# Dependencies
pip install -r requirements.txt

# .env dosyasını düzenle
cp .env.example .env

# Çalıştır
python app.py
```

## Kullanım

- **Visitor**: http://localhost:5000
- **Admin**: http://localhost:5000/login
- **Test Dashboard**: http://localhost:5000/test (Admin only)

## Deployment

### Railway (Önerilen)
```bash
# Railway CLI kurulum
curl -fsSL https://railway.app/install.sh | sh

# Login
railway login

# Proje oluştur
railway init

# Environment variables ayarla
railway variables set SECRET_KEY=your-secret-key
railway variables set ADMIN_USERNAME=admin
railway variables set ADMIN_PASSWORD=your-password
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set TELEGRAM_CHAT_ID=your_chat_id
railway variables set CLOUDINARY_CLOUD_NAME=your_cloud_name
railway variables set CLOUDINARY_API_KEY=your_api_key
railway variables set CLOUDINARY_API_SECRET=your_api_secret

# Deploy
railway up
```

### Render
Render için `render.yaml` hazır. Environment variables ekle ve deploy et.

### Vercel
Vercel için `vercel.json` ve `api/app.py` hazır. Environment variables ekle ve deploy et.

## Güvenlik

- XSS koruması aktif (Bleach + escapeHtml)
- CSRF koruması (Flask-WTF)
- Rate limiting uygulanmış
- Input validation
- Güvenli session yönetimi
- SQL injection koruması
- Path traversal koruması
- Log injection koruması

## Test Dashboard

Enterprise-level test dashboard ile:
- 120 comprehensive test (15 per category)
- 50 auto-repair operations
- Real-time monitoring
- Mobile-optimized interface

```bash
# Health check
curl http://localhost:5000/health

# Test dashboard (admin only)
# http://localhost:5000/test
```

Detaylı dokümantasyon için `SYSTEM_DOCS/` klasörüne bakın.
