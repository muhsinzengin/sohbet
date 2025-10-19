# CHANGELOG

## [2.1] - 2024

### 🔴 Kritik Düzeltmeler

#### PostgreSQL Tam Uyumluluğu
- ✅ NOW() fonksiyonu kullanımı
- ✅ RealDictCursor düzeltmesi
- ✅ NULLS LAST → COALESCE dönüşümü
- ✅ Heartbeat timestamp Python tarafında

#### Mesaj Kaybı Önleme
- ✅ Temp threadID kaldırıldı
- ✅ Buton kilitleme sistemi
- ✅ localStorage persistence
- ✅ Rejoin eventi

#### Telegram Stabilite
- ✅ asyncio.run → ThreadPoolExecutor
- ✅ v20 uyumlu başlatma
- ✅ Event loop çakışması önlendi

### 🟡 Yüksek Öncelikli Düzeltmeler

#### Güvenlik İyileştirmeleri
- ✅ CORS whitelist (production)
- ✅ Secure cookies
- ✅ SESSION_COOKIE_HTTPONLY
- ✅ SESSION_COOKIE_SAMESITE

#### Upload Güvenliği
- ✅ Content-type validasyonu
- ✅ Error handling
- ✅ Try-except blokları

#### Socket.IO Optimizasyonu
- ✅ Production: eventlet
- ✅ Development: threading
- ✅ Koşullu async_mode

### 🟢 Orta Öncelikli Düzeltmeler

#### Database İyileştirmeleri
- ✅ SQLite foreign keys aktif
- ✅ telegram_links temizleme

#### Logging Sistemi
- ✅ Python logging modülü
- ✅ Structured logging
- ✅ Log levels

### 📝 Kod Değişiklikleri

**Değiştirilen Dosyalar:**
- `database.py` - PostgreSQL uyumu, foreign keys
- `app.py` - Security, validation, logging
- `static/js/index.js` - Buton kilitleme, persistence
- `.env.example` - CORS ayarı

**Satır Değişikliği:** ~300 satır

### ⏳ Bilinen Sorunlar

1. **OTP Kalıcılığı** - In-memory storage, multi-worker'da sorun
2. **Telegram Medya** - Sadece text destekleniyor

### 🔄 Migration Notları

#### Database
```bash
# Eski database'i sil (schema değişti)
del data/chat.db

# Yeni schema otomatik oluşturulacak
python app.py
```

#### Environment Variables
```bash
# .env dosyasına ekle
CORS_ORIGINS=*  # Production'da domain listesi
```

### 📊 Performans İyileştirmeleri

- Socket.IO eventlet modu (production)
- Foreign key constraints (data integrity)
- Logging sistemi (debugging)

### 🧪 Test Gereksinimleri

- [ ] PostgreSQL bağlantı testi
- [ ] Foreign key constraint testi
- [ ] Upload validasyon testi
- [ ] Session security testi
- [ ] Telegram bot testi

---

## [2.0] - 2024

### İlk Sürüm
- Flask + Socket.IO
- Telegram OTP
- SQLite/PostgreSQL dual support
- Cloudinary entegrasyonu
- Mobile-first design

---

**Versiyon:** 2.1  
**Durum:** Stable  
**Önceki Versiyon:** 2.0
