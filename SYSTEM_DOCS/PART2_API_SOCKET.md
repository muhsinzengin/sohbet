# PART 2: API & SOCKET.IO DOCUMENTATION

## 6. API ENDPOINTS

### 6.1 Public Routes

#### GET /
**Açıklama:** Visitor chat sayfası  
**Template:** index.html  
**Auth:** Yok  
**Response:** HTML page

#### GET /login
**Açıklama:** Admin login sayfası  
**Template:** login.html  
**Auth:** Yok  
**Response:** HTML page

#### GET /favicon.ico
**Açıklama:** Favicon request handler  
**Response:** 204 No Content

### 6.2 Authentication Routes

#### POST /request-otp
**Açıklama:** OTP kodu oluştur ve Telegram'a gönder  
**Auth:** Yok  
**Request:** JSON (boş)  
**Response:**
```json
{
  "success": true,
  "otp": "123456",  // Sadece development'ta
  "message": "OTP Telegram'a gönderildi"
}
```

**Akış:**
1. 6 haneli random OTP oluştur
2. 5 dakika geçerlilik süresi ile otp_store'a kaydet
3. Telegram bot varsa → Telegram'a gönder
4. Telegram bot yoksa → Response'da göster (development)

#### POST /verify-otp
**Açıklama:** OTP kodunu doğrula ve session oluştur  
**Auth:** Yok  
**Request:**
```json
{
  "otp": "123456"
}
```
**Response:**
```json
{
  "success": true,
  "redirect": "/admin"
}
```

**Validasyon:**
- OTP istendi mi?
- Süresi doldu mu?
- Kod doğru mu?

#### GET /admin
**Açıklama:** Admin panel sayfası  
**Template:** admin.html  
**Auth:** session['admin'] = True  
**Redirect:** /login (auth yoksa)

#### GET /logout
**Açıklama:** Admin session'ı sonlandır  
**Auth:** Yok  
**Redirect:** /login

### 6.3 API Routes (Admin Only)

#### GET /api/threads
**Açıklama:** Tüm thread'leri listele  
**Auth:** session['admin']  
**Response:**
```json
[
  {
    "id": "uuid",
    "display_name": "Ahmet",
    "created_at": "2024-01-01 12:00:00",
    "last_activity_at": "2024-01-01 12:30:00",
    "last_message": "Merhaba",
    "last_message_time": "2024-01-01 12:30:00"
  }
]
```

**SQL Query:**
```sql
SELECT t.*, 
       (SELECT content_text FROM messages 
        WHERE thread_id = t.id 
        ORDER BY created_at DESC LIMIT 1) as last_message,
       (SELECT created_at FROM messages 
        WHERE thread_id = t.id 
        ORDER BY created_at DESC LIMIT 1) as last_message_time
FROM threads t
ORDER BY last_message_time DESC NULLS LAST
```

#### GET /api/messages?thread_id=X
**Açıklama:** Belirli thread'in mesajlarını getir  
**Auth:** session['admin']  
**Query Params:** thread_id (required)  
**Response:**
```json
[
  {
    "id": "uuid",
    "thread_id": "uuid",
    "sender": "visitor",
    "type": "text",
    "content_text": "Merhaba",
    "file_path": null,
    "created_at": "2024-01-01 12:00:00"
  }
]
```

**SQL Query:**
```sql
SELECT * FROM messages 
WHERE thread_id = ? 
ORDER BY created_at ASC
```

#### POST /api/upload/image
**Açıklama:** Resim yükle  
**Auth:** Yok (public)  
**Content-Type:** multipart/form-data  
**Request:** file (FormData)  
**Max Size:** 16MB  
**Response:**
```json
{
  "url": "https://res.cloudinary.com/..." // Production
  "url": "/uploads/images/uuid_filename.jpg" // Development
}
```

**Akış:**
```python
if cloudinary_configured:
    result = cloudinary.uploader.upload(file, folder='chat_images')
    return jsonify({'url': result['secure_url']})
else:
    filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
    file.save(f"uploads/images/{filename}")
    return jsonify({'url': f'/uploads/images/{filename}'})
```

#### POST /api/upload/audio
**Açıklama:** Ses dosyası yükle  
**Auth:** Yok (public)  
**Content-Type:** multipart/form-data  
**Request:** file (FormData)  
**Max Size:** 16MB  
**Response:**
```json
{
  "url": "https://res.cloudinary.com/..." // Production
  "url": "/uploads/audio/uuid.webm" // Development
}
```

**Akış:**
```python
if cloudinary_configured:
    result = cloudinary.uploader.upload(file, folder='chat_audio', resource_type='video')
    return jsonify({'url': result['secure_url']})
else:
    filename = f"{uuid.uuid4()}.webm"
    file.save(f"uploads/audio/{filename}")
    return jsonify({'url': f'/uploads/audio/{filename}'})
```

#### GET /uploads/<folder>/<filename>
**Açıklama:** Local upload'ları serve et (development only)  
**Auth:** Yok  
**Response:** File

#### POST /api/messages/clear?thread_id=X
**Açıklama:** Belirli thread'in mesajlarını sil  
**Auth:** session['admin']  
**Query Params:** thread_id (required)  
**Response:**
```json
{
  "success": true
}
```

**SQL:**
```sql
DELETE FROM messages WHERE thread_id = ?
```

#### POST /api/messages/clear_all
**Açıklama:** Tüm mesajları ve thread'leri sil  
**Auth:** session['admin']  
**Response:**
```json
{
  "success": true
}
```

**SQL:**
```sql
DELETE FROM messages;
DELETE FROM threads;
DELETE FROM telegram_links;
```

---

## 7. SOCKET.IO EVENTS

### 7.1 Client → Server Events

#### 'join'
**Gönderen:** Visitor  
**Açıklama:** Yeni thread oluştur ve visitor'ı room'a ekle  
**Data:**
```javascript
{
  display_name: "Ahmet"
}
```
**Response Event:** 'joined'  
**Server Akışı:**
```python
1. UUID thread_id oluştur
2. Database'e thread kaydet
3. Visitor'ı thread_id room'una ekle
4. 'joined' event'i emit et
```

#### 'admin_join'
**Gönderen:** Admin  
**Açıklama:** Admin'i 'admin_room'a ekle  
**Data:** Yok  
**Server Akışı:**
```python
join_room('admin_room')
```

#### 'heartbeat'
**Gönderen:** Visitor (30 saniyede bir)  
**Açıklama:** Online status güncelle  
**Data:**
```javascript
{
  thread_id: "uuid"
}
```
**Server Akışı:**
```python
1. threads.last_activity_at güncelle (Türkiye saati)
2. 'visitor_online' event'i admin_room'a emit et
```

#### 'message_to_admin'
**Gönderen:** Visitor  
**Açıklama:** Visitor'dan admin'e mesaj  
**Data:**
```javascript
{
  thread_id: "uuid",
  type: "text",  // "text", "image", "audio"
  text: "Merhaba",  // type=text için
  file_url: "https://..."  // type=image/audio için
}
```
**Server Akışı:**
```python
1. UUID message_id oluştur
2. Database'e mesaj kaydet (sender='visitor')
3. 'message_from_visitor' event'i admin_room'a emit et
4. Eğer type='text' ve Telegram aktifse:
   a. Telegram'a bildirim gönder
   b. telegram_links tablosuna kaydet
```

#### 'message_to_visitor'
**Gönderen:** Admin  
**Açıklama:** Admin'den visitor'a mesaj  
**Data:**
```javascript
{
  thread_id: "uuid",
  type: "text",
  text: "Merhaba",
  file_url: "https://..."
}
```
**Server Akışı:**
```python
1. UUID message_id oluştur
2. Database'e mesaj kaydet (sender='admin')
3. 'message_from_admin' event'i thread_id room'una emit et
4. 'message_from_telegram' event'i admin_room'a emit et (sync için)
```

### 7.2 Server → Client Events

#### 'joined'
**Alıcı:** Visitor  
**Açıklama:** Thread oluşturuldu, thread_id döndür  
**Data:**
```javascript
{
  thread_id: "uuid"
}
```

#### 'message_from_visitor'
**Alıcı:** Admin (admin_room)  
**Açıklama:** Visitor'dan yeni mesaj geldi  
**Data:**
```javascript
{
  id: "uuid",
  thread_id: "uuid",
  sender: "visitor",
  type: "text",
  content_text: "Merhaba",
  file_path: null,
  created_at: "2024-01-01 12:00:00"
}
```

#### 'message_from_admin'
**Alıcı:** Visitor (thread_id room)  
**Açıklama:** Admin'den yeni mesaj geldi  
**Data:**
```javascript
{
  id: "uuid",
  thread_id: "uuid",
  sender: "admin",
  type: "text",
  content_text: "Merhaba",
  file_path: null,
  created_at: "2024-01-01 12:00:00"
}
```

#### 'message_from_telegram'
**Alıcı:** Admin (admin_room)  
**Açıklama:** Telegram'dan gelen mesaj (sync için)  
**Data:**
```javascript
{
  id: "uuid",
  thread_id: "uuid",
  sender: "admin",
  type: "text",
  content_text: "Merhaba",
  file_path: null,
  created_at: "2024-01-01 12:00:00"
}
```

#### 'visitor_online'
**Alıcı:** Admin (admin_room)  
**Açıklama:** Visitor online (heartbeat geldi)  
**Data:**
```javascript
{
  thread_id: "uuid"
}
```

### 7.3 Socket.IO Configuration

```python
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",  # CORS enabled
    async_mode='threading'      # Threading mode
)
```

**Client Configuration:**
```javascript
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,
    timeout: 30000,
    upgrade: true,
    rememberUpgrade: true
});
```

---

