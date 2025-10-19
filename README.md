# Flask Chat Uygulaması

Modern, gerçek zamanlı chat uygulaması - Telegram OTP entegrasyonlu

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
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set TELEGRAM_ADMIN_ID=your_admin_id
railway variables set CLOUDINARY_URL=your_cloudinary_url
railway variables set DATABASE_URL=your_database_url

# Deploy
railway up
```

### Render
Render için `render.yaml` hazır. Environment variables ekle ve deploy et.

### Vercel
Vercel için `vercel.json` ve `api/app.py` hazır. Environment variables ekle ve deploy et.

## Güvenlik

- XSS koruması aktif
- Rate limiting uygulanmış
- Input validation
- Güvenli session yönetimi
- SQL injection koruması

## Test

```bash
# Güvenlik testleri
python test_security.py

# API testleri
python -c "
import requests
response = requests.get('http://localhost:5000/health')
print(response.json())
"
```

Detaylı dokümantasyon için `SYSTEM_DOCS/` klasörüne bakın.
