# Telegram Test Rehberi

## Adım 1: Bot Oluştur

1. Telegram'ı aç
2. **@BotFather** ara ve başlat
3. `/newbot` komutunu gönder
4. Bot adı gir (örn: "Test Chat Bot")
5. Bot username gir (örn: "test_chat_bot")
6. Token'ı kopyala

**Örnek Token:**
```
7234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

## Adım 2: Chat ID Al

### Yöntem 1: @userinfobot (Kolay)
1. Telegram'da **@userinfobot** ara
2. `/start` yaz
3. "Id:" yazan sayıyı kopyala

**Örnek Chat ID:**
```
123456789
```

### Yöntem 2: API (Manuel)
1. Botuna `/start` yaz
2. Tarayıcıda aç:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
3. `"chat":{"id":123456789` kısmındaki sayıyı kopyala

## Adım 3: .env Dosyasını Güncelle

`.env` dosyasını aç ve şunları ekle:

```env
TELEGRAM_BOT_TOKEN=7234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
TELEGRAM_CHAT_ID=123456789
```

## Adım 4: Test Et

```bash
python test_telegram.py
```

**Başarılı çıktı:**
```
==================================================
TELEGRAM BOT TEST
==================================================
[OK] Token: 7234567890:AAHdqTcv...
[OK] Chat ID: 123456789

Test 1: Bot bilgilerini al...
[OK] Bot adi: @test_chat_bot
[OK] Bot ID: 7234567890

Test 2: Test mesaji gonder...
[OK] Mesaj gonderildi! Message ID: 123

Test 3: Son mesajlari kontrol et...
[OK] 1 mesaj bulundu

==================================================
[OK] TUM TESTLER BASARILI!
==================================================
```

## Adım 5: Uygulamayı Başlat

```bash
python app.py
```

**Görmek istediğin:**
```
Database initialized
Telegram bot started
Server starting on http://localhost:5000
```

## Adım 6: Tam Test

### Test 1: Visitor → Telegram
1. http://localhost:5000 aç
2. İsim gir ve sohbete başla
3. Mesaj yaz: "Merhaba"
4. Telegram'da bildirim geldi mi kontrol et

### Test 2: Telegram → Visitor
1. Telegram'da gelen mesaja **Reply** yap
2. "Selam!" yaz
3. Visitor sayfasında mesajın göründüğünü kontrol et

### Test 3: Admin Panel
1. http://localhost:5000/login aç
2. OTP iste ve gir
3. Thread'i seç
4. Mesajları gör
5. Yanıt yaz

## Sorun Giderme

### "TELEGRAM_BOT_TOKEN bulunamadi"
- `.env` dosyasını kontrol et
- Token'ı doğru kopyaladın mı?
- Tırnak işareti kullanma

### "Chat ID yanlis"
- @userinfobot ile tekrar dene
- Negatif ID ise eksi işaretini de kopyala

### "Telegram bot disabled"
- `.env` dosyasını kaydettin mi?
- Uygulamayı yeniden başlattın mı?

### Mesaj gelmiyor
- Botuna `/start` yazdın mı?
- Token doğru mu?
- İnternet bağlantın var mı?

## Başarı Kriterleri

✅ Test scripti başarılı  
✅ Telegram'da test mesajı geldi  
✅ Visitor mesajı Telegram'a ulaştı  
✅ Telegram reply'i visitor'a ulaştı  
✅ Admin panelinde görünüyor  

Hepsi tamam mı? **Sistem hazır!** 🚀
