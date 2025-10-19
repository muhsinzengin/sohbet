# Flask Chat Uygulaması

Modern, gerçek zamanlı chat uygulaması - Telegram OTP entegrasyonlu

## Özellikler

- ✅ Gerçek zamanlı mesajlaşma (Socket.IO)
- ✅ Telegram OTP ile güvenli admin girişi
- ✅ SQLite/PostgreSQL dual support
- ✅ Dosya yükleme (resim, ses)
- ✅ Cloudinary entegrasyonu
- ✅ Mobile-first responsive tasarım
- ✅ Render deployment ready

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

Render için `render.yaml` hazır. Environment variables ekle ve deploy et.

Detaylı dokümantasyon için `hazırlık/` klasörüne bakın.
