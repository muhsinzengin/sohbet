# PART 3: TELEGRAM & TIME MANAGEMENT

## 8. TELEGRAM ENTEGRASYONU

### 8.1 Telegram Bot Yapısı

**Kütüphane:** python-telegram-bot 20.7

**Initialization:**
```python
if Config.TELEGRAM_BOT_TOKEN:
    from telegram import Bot, Update
    from telegram.ext import Application, MessageHandler, filters, ContextTypes
    import threading
    
    telegram_bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    telegram_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
```

### 8.2 Mesaj Akışları

#### Visitor → Telegram (Bildirim)

**Akış:**
```
1. Visitor mesaj gönderir (Socket.IO: message_to_admin)
2. Server mesajı database'e kaydeder
3. Server Telegram'a bildirim gönderir
4. Server telegram_links tablosuna kaydeder
```

**Kod:**
```python
@socketio.on('message_to_admin')
def handle_message_to_admin(data):
    # ... mesaj kaydedildi ...
    
    if telegram_bot and Config.TELEGRAM_CHAT_ID and msg_type == 'text':
        thread = db.execute_query(
            'SELECT display_name FROM threads WHERE id = ?', 
            (thread_id,), 
            fetch='one'
        )
        if thread:
            async def send_telegram():
                tg_msg = await telegram_bot.send_message(
                    chat_id=Config.TELEGRAM_CHAT_ID,
                    text=f"💬 {thread['display_name']}\n\n{content_text}"
                )
                # Link kaydet
                db.execute_query(
                    'INSERT INTO telegram_links (thread_id, tg_chat_id, tg_message_id) VALUES (?, ?, ?)',
                    (thread_id, str(tg_msg.chat_id), tg_msg.message_id),
                    fetch=None
                )
            
            asyncio.run(send_telegram())
```

**Telegram Mesajı:**
```
💬 Ahmet

Merhaba, yardım alabilir miyim?
```

#### Telegram → Visitor (Reply)

**Akış:**
```
1. Admin Telegram'da mesaja reply yapar
2. Bot reply'i yakalar (handle_telegram_message)
3. telegram_links'ten thread_id bulur
4. Mesajı database'e kaydeder
5. Socket.IO ile visitor'a iletir
6. Admin paneline sync eder
```

**Kod:**
```python
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    # Reply kontrolü
    if update.message.reply_to_message:
        reply_to_id = update.message.reply_to_message.message_id
        
        # Thread ID bul
        link = db.execute_query(
            'SELECT thread_id FROM telegram_links WHERE tg_message_id = ?',
            (reply_to_id,),
            fetch='one'
        )
        
        if link:
            thread_id = link['thread_id']
            msg_id = str(uuid.uuid4())
            content_text = update.message.text
            
            # Database'e kaydet
            db.execute_query(
                'INSERT INTO messages (id, thread_id, sender, type, content_text, file_path) VALUES (?, ?, ?, ?, ?, ?)',
                (msg_id, thread_id, 'admin', 'text', content_text, ''),
                fetch=None
            )
            
            # Visitor'a ilet
            msg = db.execute_query('SELECT * FROM messages WHERE id = ?', (msg_id,), fetch='one')
            socketio.emit('message_from_admin', msg, room=thread_id)
            socketio.emit('message_from_telegram', msg, room='admin_room')
```

### 8.3 Telegram Bot Background Thread

**Başlatma:**
```python
def start_telegram_bot():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_app.initialize())
    loop.run_until_complete(telegram_app.start())
    loop.run_until_complete(telegram_app.updater.start_polling())
    loop.run_forever()

telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
telegram_thread.start()
print('Telegram bot started')
```

**Özellikler:**
- Daemon thread (uygulama kapanınca otomatik kapanır)
- Kendi event loop'u var
- Polling mode (webhook değil)
- Background'da sürekli çalışır

### 8.4 telegram_links Tablosu

**Amaç:** Telegram mesajları ile thread'leri eşleştir

**Şema:**
```sql
CREATE TABLE telegram_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    tg_chat_id TEXT NOT NULL,
    tg_message_id INTEGER NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```

**Kullanım:**
```python
# Telegram'a mesaj gönderirken kaydet
tg_msg = await telegram_bot.send_message(...)
db.execute_query(
    'INSERT INTO telegram_links (thread_id, tg_chat_id, tg_message_id) VALUES (?, ?, ?)',
    (thread_id, str(tg_msg.chat_id), tg_msg.message_id)
)

# Telegram'dan reply geldiğinde thread_id bul
link = db.execute_query(
    'SELECT thread_id FROM telegram_links WHERE tg_message_id = ?',
    (reply_to_id,), fetch='one'
)
```

### 8.5 Telegram OTP Sistemi

**Akış:**
```
1. Admin /login sayfasına gider
2. "OTP Kodu İste" butonuna tıklar
3. Server 6 haneli OTP oluşturur
4. Server Telegram'a OTP gönderir
5. Admin Telegram'dan OTP'yi alır
6. Admin OTP'yi girer
7. Server OTP'yi doğrular
8. Session oluşturulur
```

**Kod:**
```python
@app.route('/request-otp', methods=['POST'])
def request_otp():
    otp = str(random.randint(100000, 999999))
    otp_store['admin'] = {
        'code': otp, 
        'expires': datetime.now() + timedelta(minutes=5)
    }
    
    if telegram_bot and Config.TELEGRAM_CHAT_ID:
        asyncio.run(telegram_bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=f"🔐 Admin OTP Kodu: {otp}\n\n⏰ 5 dakika geçerli"
        ))
        return jsonify({'success': True})
    else:
        # Development mode
        return jsonify({'success': True, 'otp': otp})
```

### 8.6 Telegram Test

**Test Scripti:** test_telegram.py

**Testler:**
1. Bot bilgilerini al (get_me)
2. Test mesajı gönder
3. Son mesajları kontrol et (get_updates)

**Çalıştırma:**
```bash
python test_telegram.py
```

**Beklenen Çıktı:**
```
[OK] Token: 7801493894:AAHQTlDbr...
[OK] Chat ID: 6476943853
[OK] Bot adi: @Hddestek_bot
[OK] Mesaj gonderildi!
[OK] TUM TESTLER BASARILI!
```

---

## 9. ZAMAN YÖNETİMİ

### 9.1 Türkiye Saat Dilimi (UTC+3)

**Tanım:**
```python
# database.py
from datetime import datetime, timezone, timedelta

TURKEY_TZ = timezone(timedelta(hours=3))
```

### 9.2 Database Zaman Damgaları

**SQLite Default Values:**
```sql
-- Threads
created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
last_activity_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))

-- Messages
created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
```

**Heartbeat Update:**
```python
@socketio.on('heartbeat')
def handle_heartbeat(data):
    db.execute_query(
        "UPDATE threads SET last_activity_at = datetime('now', '+3 hours') WHERE id = ?",
        (thread_id,),
        fetch=None
    )
```

### 9.3 Frontend Zaman Gösterimi

**Mesaj Zamanı:**
```javascript
// index.js & admin.js
const msgDate = new Date(data.created_at);
time.textContent = msgDate.toLocaleTimeString('tr-TR', { 
    hour: '2-digit', 
    minute: '2-digit' 
});
```

**Tarih Gösterimi:**
```javascript
// admin.js
dateText = msgDate.toLocaleDateString('tr-TR', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
});
```

### 9.4 Zaman Farkı Hesaplamaları

**"Ago" Text (admin.js):**
```javascript
const now = new Date();
const diffMs = now - msgDate;
const diffMins = Math.floor(diffMs / 60000);
const diffHours = Math.floor(diffMs / 3600000);
const diffDays = Math.floor(diffMs / 86400000);

if (diffMins < 1) {
    agoText = 'Şimdi';
    timeClass = 'time-now';  // Yeşil
} else if (diffMins < 60) {
    agoText = diffMins + 'dk önce';
    timeClass = 'time-minutes';  // Mavi
} else if (diffHours < 24) {
    agoText = diffHours + 'sa önce';
    timeClass = 'time-hours';  // Turuncu
} else if (diffDays === 1) {
    agoText = 'Dün';
    timeClass = 'time-yesterday';  // Kırmızı
} else if (diffDays < 7) {
    agoText = diffDays + 'g önce';
    timeClass = 'time-days';  // Mor
} else {
    agoText = msgDate.toLocaleDateString('tr-TR', { 
        day: 'numeric', 
        month: 'short' 
    });
    timeClass = 'time-old';  // Gri
}
```

### 9.5 Zaman Renk Paleti

**CSS Classes:**
```css
.time-now { color: #10b981; }      /* Yeşil - Şimdi */
.time-minutes { color: #3b82f6; }  /* Mavi - Dakikalar */
.time-hours { color: #f59e0b; }    /* Turuncu - Saatler */
.time-yesterday { color: #ef4444; }/* Kırmızı - Dün */
.time-days { color: #8b5cf6; }     /* Mor - Günler */
.time-old { color: #6b7280; }      /* Gri - Eski */
.online-text { color: #4ade80; }   /* Yeşil - Çevrimiçi */
```

### 9.6 Online Status Sistemi

**Heartbeat Interval:**
```javascript
// index.js
setInterval(() => {
    if (threadId) {
        socket.emit('heartbeat', { thread_id: threadId });
    }
}, 30000);  // 30 saniye
```

**Online Timeout (admin.js):**
```javascript
function setThreadOnline(threadId) {
    // Mevcut timeout'u temizle
    if (onlineTimeouts.has(threadId)) {
        clearTimeout(onlineTimeouts.get(threadId));
    }
    
    // Online olarak işaretle
    onlineThreads.add(threadId);
    
    // 2 dakika sonra offline yap
    const timeout = setTimeout(() => {
        onlineThreads.delete(threadId);
        onlineTimeouts.delete(threadId);
        loadThreads();
    }, 2 * 60 * 1000);
    
    onlineTimeouts.set(threadId, timeout);
}
```

**Mantık:**
- Visitor her 30 saniyede heartbeat gönderir
- Admin 2 dakika boyunca heartbeat gelmezse offline sayar
- Online thread'ler yeşil dot ile gösterilir

### 9.7 Auto-Refresh

**Thread Listesi:**
```javascript
// admin.js
setInterval(() => {
    loadThreads();
}, 30000);  // 30 saniye
```

**Amaç:** Zaman gösterimlerini güncel tutmak ("5dk önce" → "6dk önce")

---

