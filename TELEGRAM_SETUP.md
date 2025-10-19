# Telegram Bot Kurulumu

## 1. Bot Oluştur

1. Telegram'da **@BotFather**'a git
2. `/newbot` komutunu gönder
3. Bot adı ver (örn: "My Chat Bot")
4. Bot username ver (örn: "mychat_bot")
5. Token'ı kopyala: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## 2. Chat ID Al

### Yöntem 1: Direkt
1. Botuna `/start` yaz
2. Tarayıcıda aç:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. `chat.id` değerini kopyala (örn: `987654321`)

### Yöntem 2: @userinfobot
1. Telegram'da **@userinfobot**'a git
2. `/start` yaz
3. ID'ni kopyala

## 3. .env Dosyasını Güncelle

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

## 4. Uygulamayı Yeniden Başlat

```bash
python app.py
```

## Nasıl Çalışır?

### Visitor → Admin
1. Visitor mesaj gönderir
2. Mesaj Telegram'a bildirim olarak gelir
3. Admin Telegram'dan görebilir

### Admin → Visitor (Telegram'dan)
1. Telegram'da gelen mesaja **Reply** yap
2. Yanıtın otomatik olarak visitor'a iletilir
3. Admin panelinde de görünür

### Admin → Visitor (Web'den)
1. Admin panelinden normal mesaj gönder
2. Visitor'a ulaşır

## Test

1. Visitor sayfasından mesaj gönder
2. Telegram'da bildirim geldi mi kontrol et
3. Telegram'dan reply yap
4. Visitor'da mesaj göründü mü kontrol et

✅ Sistem hazır!
