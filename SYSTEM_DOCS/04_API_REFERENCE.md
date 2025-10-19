# 🔧 FLASK CHAT v2.3 - API REFERENCE

**Versiyon:** 2.3  
**Base URL:** `https://your-app.railway.app`  
**Content-Type:** `application/json`  

---

## 📋 **API ENDPOINTS**

### **Authentication Endpoints**

#### **POST /admin/login**
Admin girişi için OTP gönderir.

**Request:**
```json
{
  "username": "admin",
  "password": "admin_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to Telegram",
  "otp_sent": true
}
```

#### **POST /admin/verify-otp**
OTP doğrulaması yapar.

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
  "message": "Login successful",
  "session": "session_token"
}
```

---

### **Message Endpoints**

#### **GET /api/messages/{thread_id}**
Belirli thread'in mesajlarını getirir.

**Parameters:**
- `thread_id` (string): Thread ID

**Response:**
```json
{
  "success": true,
  "messages": [
    {
      "id": 1,
      "thread_id": "thread_123",
      "content_text": "Hello world",
      "content_type": "text",
      "sender_type": "visitor",
      "created_at": "2024-10-19T18:30:00Z"
    }
  ]
}
```

#### **POST /api/messages/send**
Yeni mesaj gönderir.

**Request:**
```json
{
  "thread_id": "thread_123",
  "text": "Hello admin",
  "type": "text"
}
```

**Response:**
```json
{
  "success": true,
  "message_id": 123,
  "thread_id": "thread_123"
}
```

#### **GET /api/threads**
Tüm thread'leri getirir (Admin only).

**Response:**
```json
{
  "success": true,
  "threads": [
    {
      "id": "thread_123",
      "user_id": 1,
      "created_at": "2024-10-19T18:30:00Z",
      "last_activity": "2024-10-19T18:35:00Z",
      "status": "active",
      "message_count": 5
    }
  ]
}
```

#### **POST /api/messages/clear**
Thread mesajlarını temizler.

**Request:**
```json
{
  "thread_id": "thread_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Messages cleared"
}
```

---

### **File Upload Endpoints**

#### **POST /api/upload/image**
Resim dosyası yükler.

**Request:** `multipart/form-data`
- `file`: Image file (JPEG, PNG, GIF)

**Response:**
```json
{
  "success": true,
  "file_path": "/uploads/images/uuid.jpg",
  "file_url": "https://res.cloudinary.com/...",
  "message": "Image uploaded successfully"
}
```

#### **POST /api/upload/audio**
Ses dosyası yükler.

**Request:** `multipart/form-data`
- `file`: Audio file (MP3, WAV, OGG)

**Response:**
```json
{
  "success": true,
  "file_path": "/uploads/audio/uuid.mp3",
  "file_url": "https://res.cloudinary.com/...",
  "message": "Audio uploaded successfully"
}
```

---

### **Health Check Endpoints**

#### **GET /health**
Uygulama sağlık durumunu kontrol eder.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-19T18:30:00Z",
  "version": "2.3",
  "environment": "production",
  "checks": {
    "database": "healthy",
    "telegram": "healthy",
    "memory": {
      "used_percent": 45.2,
      "available_gb": 0.28
    },
    "disk": {
      "used_percent": 12.5,
      "free_gb": 0.88
    }
  }
}
```

#### **GET /health/live**
Liveness probe endpoint.

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2024-10-19T18:30:00Z"
}
```

#### **GET /health/ready**
Readiness probe endpoint.

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2024-10-19T18:30:00Z"
}
```

---

## 🔌 **SOCKET.IO EVENTS**

### **Client → Server Events**

#### **connect**
Socket.IO bağlantısı kurulur.

**Emit:**
```javascript
socket.emit('connect');
```

#### **message_from_visitor**
Ziyaretçi mesajı gönderir.

**Emit:**
```javascript
socket.emit('message_from_visitor', {
  thread_id: 'thread_123',
  text: 'Hello admin',
  type: 'text'
});
```

#### **message_to_admin**
Admin'e mesaj gönderir.

**Emit:**
```javascript
socket.emit('message_to_admin', {
  thread_id: 'thread_123',
  text: 'Hello visitor',
  type: 'text'
});
```

#### **message_to_visitor**
Ziyaretçiye mesaj gönderir.

**Emit:**
```javascript
socket.emit('message_to_visitor', {
  thread_id: 'thread_123',
  text: 'Hello visitor',
  type: 'text'
});
```

#### **join_thread**
Thread'e katılır.

**Emit:**
```javascript
socket.emit('join_thread', {
  thread_id: 'thread_123'
});
```

#### **leave_thread**
Thread'den ayrılır.

**Emit:**
```javascript
socket.emit('leave_thread', {
  thread_id: 'thread_123'
});
```

---

### **Server → Client Events**

#### **message_from_visitor**
Ziyaretçi mesajı alındı.

**Listen:**
```javascript
socket.on('message_from_visitor', (data) => {
  console.log('Visitor message:', data);
  // data: { id, thread_id, content_text, sender_type, created_at }
});
```

#### **message_to_admin**
Admin'e mesaj gönderildi.

**Listen:**
```javascript
socket.on('message_to_admin', (data) => {
  console.log('Message to admin:', data);
  // data: { id, thread_id, content_text, sender_type, created_at }
});
```

#### **message_to_visitor**
Ziyaretçiye mesaj gönderildi.

**Listen:**
```javascript
socket.on('message_to_visitor', (data) => {
  console.log('Message to visitor:', data);
  // data: { id, thread_id, content_text, sender_type, created_at }
});
```

#### **thread_created**
Yeni thread oluşturuldu.

**Listen:**
```javascript
socket.on('thread_created', (data) => {
  console.log('New thread:', data);
  // data: { id, user_id, created_at, status }
});
```

#### **user_online**
Kullanıcı online oldu.

**Listen:**
```javascript
socket.on('user_online', (data) => {
  console.log('User online:', data);
  // data: { user_id, username, last_seen }
});
```

#### **user_offline**
Kullanıcı offline oldu.

**Listen:**
```javascript
socket.on('user_offline', (data) => {
  console.log('User offline:', data);
  // data: { user_id, username, last_seen }
});
```

#### **message_error**
Mesaj hatası oluştu.

**Listen:**
```javascript
socket.on('message_error', (data) => {
  console.error('Message error:', data);
  // data: { type, message, code }
});
```

#### **connect_error**
Bağlantı hatası oluştu.

**Listen:**
```javascript
socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
});
```

---

## 🔐 **AUTHENTICATION**

### **Session Management**
```javascript
// Session cookie otomatik yönetilir
// CSRF token gerekli
const csrfToken = document.querySelector('meta[name=csrf-token]').content;
```

### **CSRF Protection**
```javascript
// Socket.IO bağlantısında CSRF token
const socket = io({
  extraHeaders: {
    'X-CSRFToken': getCsrfToken()
  }
});
```

---

## 📊 **ERROR HANDLING**

### **HTTP Error Codes**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `413` - File Too Large
- `429` - Rate Limited
- `500` - Internal Server Error
- `503` - Service Unavailable

### **Error Response Format**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "status": 400
}
```

### **Socket.IO Error Events**
```javascript
socket.on('message_error', (data) => {
  // data: { type, message, code }
  if (data.type === 'csrf_error') {
    console.error('CSRF token missing');
  } else if (data.type === 'validation_error') {
    console.error('Validation failed:', data.message);
  }
});
```

---

## 🚀 **PERFORMANCE**

### **Rate Limiting**
- **Message sending**: 10 requests/minute
- **File upload**: 5 requests/minute
- **API calls**: 100 requests/minute

### **Caching**
- **Messages**: 3 minutes TTL
- **Threads**: 5 minutes TTL
- **User data**: 10 minutes TTL

### **File Upload Limits**
- **Image files**: 5MB max
- **Audio files**: 10MB max
- **Allowed formats**: JPEG, PNG, GIF, MP3, WAV, OGG

---

## 🔧 **DEVELOPMENT**

### **Local Testing**
```bash
# Start development server
python app.py

# Test endpoints
curl http://localhost:5000/health
curl http://localhost:5000/api/threads
```

### **Socket.IO Testing**
```javascript
// Connect to local server
const socket = io('http://localhost:5000');

// Test message
socket.emit('message_from_visitor', {
  thread_id: 'test_thread',
  text: 'Test message',
  type: 'text'
});
```

---

## 📚 **EXAMPLES**

### **Complete Chat Flow**
```javascript
// 1. Connect to server
const socket = io('https://your-app.railway.app');

// 2. Join thread
socket.emit('join_thread', { thread_id: 'thread_123' });

// 3. Send message
socket.emit('message_from_visitor', {
  thread_id: 'thread_123',
  text: 'Hello admin!',
  type: 'text'
});

// 4. Listen for responses
socket.on('message_to_visitor', (data) => {
  console.log('Admin replied:', data.content_text);
});

// 5. Handle errors
socket.on('message_error', (data) => {
  console.error('Error:', data.message);
});
```

### **File Upload Example**
```javascript
// Upload image
const formData = new FormData();
formData.append('file', imageFile);

fetch('/api/upload/image', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    // Send message with image
    socket.emit('message_from_visitor', {
      thread_id: 'thread_123',
      type: 'image',
      file_url: data.file_url
    });
  }
});
```

---

## 🎯 **BEST PRACTICES**

### **API Usage**
- ✅ **Use HTTPS** - Always use secure connections
- ✅ **Handle errors** - Implement proper error handling
- ✅ **Rate limiting** - Respect rate limits
- ✅ **CSRF tokens** - Include CSRF tokens in requests

### **Socket.IO Usage**
- ✅ **Reconnection** - Handle connection drops
- ✅ **Error handling** - Listen for error events
- ✅ **Room management** - Join/leave rooms properly
- ✅ **Message validation** - Validate data before sending

---

**Son Güncelleme:** 2024  
**Versiyon:** 2.3  
**Status:** Production Ready ✅
