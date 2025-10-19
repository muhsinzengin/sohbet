# SYSTEM_DOCS - SİSTEM DOKÜMANTASYONU

## ⚠️ ÖNEMLİ UYARI

**BU KLASÖR ASLA SİLİNMEMELİDİR!**

Bu klasör sistemin tüm detaylı dokümantasyonunu içerir. Herhangi bir değişiklik yapıldığında bu dokümantasyon güncellenmelidir.

---

## 📚 Dokümantasyon Yapısı

### Ana Dokümantasyon
- **COMPLETE_SYSTEM_DOCUMENTATION.md** - Proje genel bakış, dosya yapısı, backend mimarisi

### Detaylı Bölümler
- **PART2_API_SOCKET.md** - API endpoints ve Socket.IO events
- **PART3_TELEGRAM_TIME.md** - Telegram entegrasyonu ve zaman yönetimi
- **PART4_DATABASE_FRONTEND.md** - Database şeması ve frontend mimarisi

### Bug Fix ve Değişiklikler
- **BUGFIX_LOG.md** - Tüm bug fix'lerin detaylı logu
- **CHANGELOG.md** - Versiyon değişiklik geçmişi
- **VERSION_INFO.md** - Versiyon bilgileri ve istatistikler

### Bu Dosya
- **README.md** - Dokümantasyon rehberi

---

## 🎯 Kullanım

### Yeni Özellik Eklendiğinde
1. İlgili bölüm dosyasını aç
2. Yeni özelliği dokümante et
3. Kod örnekleri ekle
4. Akış diyagramları güncelle

### Değişiklik Yapıldığında
1. Etkilenen bölümleri belirle
2. Güncel bilgileri yaz
3. Eski bilgileri sil veya güncelle
4. Versiyon notunu güncelle

### Sorun Giderme
1. İlgili bölümü oku
2. Kod örneklerini kontrol et
3. Akış diyagramlarını incele
4. Test senaryolarını çalıştır

---

## 📖 Dokümantasyon İçeriği

### COMPLETE_SYSTEM_DOCUMENTATION.md
- Proje genel bakış
- Dosya yapısı ve açıklamaları
- Backend mimarisi (app.py, config.py, database.py)
- Teknoloji stack
- Özellikler listesi

### PART2_API_SOCKET.md
- 11 API endpoint detayları
- Request/Response örnekleri
- 9 Socket.IO event
- Client-Server iletişimi
- Socket.IO konfigürasyonu

### PART3_TELEGRAM_TIME.md
- Telegram bot yapısı
- Mesaj akışları (Visitor→Telegram, Telegram→Visitor)
- telegram_links tablosu
- OTP sistemi
- Türkiye saat dilimi (UTC+3)
- Zaman hesaplamaları
- Online status sistemi

### PART4_DATABASE_FRONTEND.md
- 3 tablo şeması (threads, messages, telegram_links)
- Database queries
- SQLite vs PostgreSQL
- index.js (Visitor JavaScript)
- admin.js (Admin JavaScript)
- Three.js particle system

---

## 🔄 Güncelleme Kuralları

### Zorunlu Güncelleme Gereken Durumlar
1. ✅ Yeni API endpoint eklendi
2. ✅ Yeni Socket.IO event eklendi
3. ✅ Database şeması değişti
4. ✅ Yeni özellik eklendi
5. ✅ Önemli bug fix yapıldı
6. ✅ Konfigürasyon değişti
7. ✅ Deployment süreci değişti

### Güncelleme Formatı
```markdown
## X.X Özellik Adı

**Tarih:** YYYY-MM-DD  
**Versiyon:** X.X  
**Değişiklik Tipi:** Yeni Özellik / Bug Fix / İyileştirme

**Açıklama:**
...

**Kod Örneği:**
```python
...
```

**Etkilenen Dosyalar:**
- app.py
- database.py
...
```

---

## 📊 Dokümantasyon İstatistikleri

**Toplam Satır:** ~2000+ satır  
**Toplam Dosya:** 5 dosya  
**Kod Örneği:** 50+ örnek  
**Tablo/Şema:** 10+ şema  
**Akış Diyagramı:** 15+ akış

---

## 🎓 Öğrenme Yolu

### Yeni Geliştirici İçin
1. COMPLETE_SYSTEM_DOCUMENTATION.md oku (Genel bakış)
2. PART4_DATABASE_FRONTEND.md oku (Database ve UI)
3. PART2_API_SOCKET.md oku (API ve Socket)
4. PART3_TELEGRAM_TIME.md oku (Telegram ve Zaman)
5. Kod örneklerini çalıştır
6. Test senaryolarını dene

### Belirli Özellik İçin
1. İlgili bölümü bul (Ctrl+F)
2. Kod örneğini oku
3. Akış diyagramını incele
4. Test et

---

## 🛠️ Bakım

### Haftalık
- [ ] Yeni değişiklikleri dokümante et
- [ ] Kod örneklerini test et
- [ ] Bozuk linkleri düzelt

### Aylık
- [ ] Tüm dokümantasyonu gözden geçir
- [ ] Güncel olmayan bilgileri güncelle
- [ ] Yeni örnekler ekle

### Yıllık
- [ ] Büyük refactoring yap
- [ ] Versiyon numarasını güncelle
- [ ] Arşiv oluştur

---

## 📞 İletişim

**Proje Sahibi:** [Adınız]  
**Son Güncelleme:** 2024  
**Versiyon:** 2.1  
**Durum:** Production Ready (Bug Fixed)  
**Bug Fixes:** 16 düzeltme

---

## ⚖️ Lisans

Bu dokümantasyon projenin bir parçasıdır ve aynı lisans altındadır.

---

**NOT:** Bu klasör ve içeriği projenin kritik bir parçasıdır. Silme, taşıma veya değiştirme işlemlerinde dikkatli olun!
