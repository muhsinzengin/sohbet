# PART 4: DATABASE & FRONTEND

## 5. DATABASE ŞEMASI

### 5.1 Tablo: threads

**Amaç:** Konuşma thread'lerini saklar

**Şema:**
```sql
CREATE TABLE threads (
    id TEXT PRIMARY KEY,                    -- UUID
    display_name TEXT NOT NULL,             -- Ziyaretçi adı
    created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours')),
    last_activity_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
);
```

**Index:**
```sql
CREATE INDEX idx_threads_activity ON threads(last_activity_at);
```

**Örnek Veri:**
```
id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
display_name: "Ahmet"
created_at: "2024-01-15 14:30:00"
last_activity_at: "2024-01-15 14:35:00"
```

### 5.2 Tablo: messages

**Amaç:** Tüm mesajları saklar

**Şema:**
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,                    -- UUID
    thread_id TEXT NOT NULL,                -- Foreign Key
    sender TEXT NOT NULL,                   -- 'visitor' veya 'admin'
    type TEXT NOT NULL,                     -- 'text', 'image', 'audio'
    content_text TEXT,                      -- Metin içeriği (type=text için)
    file_path TEXT,                         -- Dosya yolu/URL (type=image/audio için)
    created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours')),
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_created ON messages(created_at);
```

**Örnek Veri:**
```
id: "msg-uuid-1"
thread_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
sender: "visitor"
type: "text"
content_text: "Merhaba"
file_path: null
created_at: "2024-01-15 14:30:00"
```

### 5.3 Tablo: telegram_links

**Amaç:** Telegram mesajları ile thread'leri eşleştir

**Şema:**
```sql
CREATE TABLE telegram_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- SQLite
    -- id SERIAL PRIMARY KEY,               -- PostgreSQL
    thread_id TEXT NOT NULL,
    tg_chat_id TEXT NOT NULL,               -- Telegram chat ID
    tg_message_id INTEGER NOT NULL,         -- Telegram message ID
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_telegram_links_thread ON telegram_links(thread_id);
CREATE INDEX idx_telegram_links_tg_msg ON telegram_links(tg_message_id);
```

**Örnek Veri:**
```
id: 1
thread_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
tg_chat_id: "6476943853"
tg_message_id: 634
```

### 5.4 Database Queries

**Thread Listesi (Son Mesaj ile):**
```sql
SELECT t.*, 
       (SELECT content_text FROM messages 
        WHERE thread_id = t.id 
        ORDER BY created_at DESC LIMIT 1) as last_message,
       (SELECT created_at FROM messages 
        WHERE thread_id = t.id 
        ORDER BY created_at DESC LIMIT 1) as last_message_time
FROM threads t
ORDER BY last_message_time DESC NULLS LAST;
```

**Thread Mesajları:**
```sql
SELECT * FROM messages 
WHERE thread_id = ? 
ORDER BY created_at ASC;
```

**Telegram Link Bulma:**
```sql
SELECT thread_id FROM telegram_links 
WHERE tg_message_id = ?;
```

**Thread Silme (Cascade):**
```sql
DELETE FROM messages WHERE thread_id = ?;
DELETE FROM telegram_links WHERE thread_id = ?;
DELETE FROM threads WHERE id = ?;
```

### 5.5 SQLite vs PostgreSQL

**Farklar:**

| Özellik | SQLite | PostgreSQL |
|---------|--------|------------|
| Placeholder | ? | %s |
| Auto Increment | AUTOINCREMENT | SERIAL |
| Connection | File-based | Network |
| Concurrent Writes | Limited | Full support |
| Production | ❌ | ✅ |

**Otomatik Dönüşüm:**
```python
# database.py
def execute_query(self, query, params=(), fetch='all'):
    query = query.replace('?', '%s') if self.is_postgres else query
    # ...
```

---

## 4. FRONTEND MİMARİSİ

### 4.1 index.js - Visitor JavaScript

**Boyut:** ~450 satır  
**Görev:** Visitor chat mantığı

**Yapı:**
```javascript
// Global Variables
const socket = io({...});
let threadId = null;
let displayName = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

// DOM Elements
const nameModal = document.getElementById('name-modal');
const chatContainer = document.getElementById('chat-container');
const displayNameInput = document.getElementById('display-name-input');
const joinBtn = document.getElementById('join-btn');
const messagesDiv = document.getElementById('messages');
const msgInput = document.getElementById('msg-input');
const sendBtn = document.getElementById('send-btn');
const imageBtn = document.getElementById('image-btn');
const audioBtn = document.getElementById('audio-btn');
const imageInput = document.getElementById('image-input');
```

**Ana Fonksiyonlar:**

1. **Join Chat:**
```javascript
joinBtn.addEventListener('click', () => {
    displayName = displayNameInput.value.trim();
    if (displayName) {
        socket.emit('join', {display_name: displayName});
        nameModal.style.display = 'none';
        chatContainer.style.display = 'flex';
    }
});

socket.on('joined', (data) => {
    threadId = data.thread_id;
    startHeartbeat();
});
```

2. **Send Message:**
```javascript
function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || !threadId) return;
    
    const msgData = {
        thread_id: threadId,
        type: 'text',
        text: text
    };
    
    socket.emit('message_to_admin', msgData);
    addMessage({...msgData, sender: 'visitor', created_at: new Date().toISOString()}, 'visitor');
    msgInput.value = '';
}
```

3. **Receive Message:**
```javascript
socket.on('message_from_admin', (data) => {
    addMessage(data, 'admin');
});
```

4. **Add Message to UI:**
```javascript
function addMessage(data, senderClass) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${senderClass}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    if (data.type === 'text') {
        bubble.textContent = data.content_text || data.text;
    } else if (data.type === 'image') {
        const img = document.createElement('img');
        img.src = data.file_path || data.file_url;
        bubble.appendChild(img);
    } else if (data.type === 'audio') {
        const audio = document.createElement('audio');
        audio.src = data.file_path || data.file_url;
        audio.controls = true;
        bubble.appendChild(audio);
    }
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date(data.created_at).toLocaleTimeString('tr-TR', {
        hour: '2-digit', minute: '2-digit'
    });
    
    bubble.appendChild(time);
    msgDiv.appendChild(bubble);
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
```

5. **Heartbeat:**
```javascript
function startHeartbeat() {
    setInterval(() => {
        if (threadId) {
            socket.emit('heartbeat', { thread_id: threadId });
        }
    }, 30000);
}
```

6. **Image Upload:**
```javascript
imageBtn.addEventListener('click', () => imageInput.click());

imageInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await fetch('/api/upload/image', {
        method: 'POST',
        body: formData
    });
    
    const data = await res.json();
    if (data.url) {
        const msgData = {
            thread_id: threadId,
            type: 'image',
            file_url: data.url
        };
        socket.emit('message_to_admin', msgData);
        addMessage({...msgData, sender: 'visitor', created_at: new Date().toISOString()}, 'visitor');
    }
});
```

7. **Audio Recording:**
```javascript
async function toggleRecording() {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (e) => {
            audioChunks.push(e.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, {type: 'audio/webm'});
            const formData = new FormData();
            formData.append('file', audioBlob, 'audio.webm');
            
            const res = await fetch('/api/upload/audio', {
                method: 'POST',
                body: formData
            });
            
            const data = await res.json();
            if (data.url) {
                const msgData = {
                    thread_id: threadId,
                    type: 'audio',
                    file_url: data.url
                };
                socket.emit('message_to_admin', msgData);
                addMessage({...msgData, sender: 'visitor', created_at: new Date().toISOString()}, 'visitor');
            }
            
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        audioBtn.textContent = '⏹️';
    } else {
        mediaRecorder.stop();
        isRecording = false;
        audioBtn.textContent = '🎤';
    }
}
```

8. **Three.js Background:**
```javascript
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas-bg'), alpha: true });

// Particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 150;
const posArray = new Float32Array(particlesCount * 3);

for (let i = 0; i < particlesCount * 3; i += 3) {
    posArray[i] = (Math.random() - 0.5) * 200;
    posArray[i + 1] = (Math.random() - 0.5) * 200;
    posArray[i + 2] = (Math.random() - 0.5) * 200;
}

particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

const particlesMaterial = new THREE.PointsMaterial({
    size: 1.2,
    color: 0x4eb3f5,
    transparent: true,
    opacity: 0.4
});

const particles = new THREE.Points(particlesGeometry, particlesMaterial);
scene.add(particles);

function animate() {
    requestAnimationFrame(animate);
    particles.rotation.x += 0.0001;
    particles.rotation.y += 0.0002;
    renderer.render(scene, camera);
}
animate();
```

### 4.2 admin.js - Admin JavaScript

**Boyut:** ~500 satır  
**Görev:** Admin panel mantığı

**Yapı:**
```javascript
// Global Variables
const socket = io({...});
let currentThreadId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let onlineThreads = new Set();
let onlineTimeouts = new Map();

// DOM Elements
const threadsDiv = document.getElementById('threads');
const messagesDiv = document.getElementById('admin-messages');
const msgInput = document.getElementById('admin-msg-input');
const sendBtn = document.getElementById('admin-send-btn');
// ...
```

**Ana Fonksiyonlar:**

1. **Load Threads:**
```javascript
async function loadThreads() {
    const res = await fetch('/api/threads');
    const threads = await res.json();
    
    threadsDiv.innerHTML = '';
    threads.forEach(thread => {
        const div = document.createElement('div');
        div.className = 'thread-item';
        if (thread.id === currentThreadId) {
            div.classList.add('active');
        }
        
        const isOnline = onlineThreads.has(thread.id);
        
        // Time formatting...
        
        div.innerHTML = `
            <div class="status-dot ${isOnline ? 'online' : 'offline'}"></div>
            <div class="thread-content">
                <div class="thread-row">
                    <div class="thread-name">${thread.display_name}</div>
                    <div class="thread-ago ${timeClass}">${agoText}</div>
                </div>
                <div class="thread-row">
                    <div class="thread-preview">${thread.last_message || 'Mesaj yok'}</div>
                    <div class="thread-date-time">
                        <span class="thread-date">${dateText}</span>
                        <span class="thread-time">${timeText}</span>
                    </div>
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => selectThread(thread.id, thread.display_name));
        threadsDiv.appendChild(div);
    });
}
```

2. **Select Thread:**
```javascript
async function selectThread(threadId, name) {
    currentThreadId = threadId;
    selectedName.textContent = name;
    
    // Mobile fullscreen
    chatPanel.classList.add('fullscreen');
    threadListEl.classList.add('hidden');
    
    const res = await fetch(`/api/messages?thread_id=${threadId}`);
    const messages = await res.json();
    
    messagesDiv.innerHTML = '';
    messages.forEach(msg => {
        const senderClass = msg.sender === 'visitor' ? 'visitor' : 'admin';
        addMessage(msg, senderClass);
    });
}
```

3. **Online Status Management:**
```javascript
function setThreadOnline(threadId) {
    if (onlineTimeouts.has(threadId)) {
        clearTimeout(onlineTimeouts.get(threadId));
    }
    
    onlineThreads.add(threadId);
    
    const timeout = setTimeout(() => {
        onlineThreads.delete(threadId);
        onlineTimeouts.delete(threadId);
        loadThreads();
    }, 2 * 60 * 1000);
    
    onlineTimeouts.set(threadId, timeout);
}

socket.on('visitor_online', (data) => {
    setThreadOnline(data.thread_id);
    loadThreads();
});
```

4. **Clear Modals:**
```javascript
function showConfirmModal(title, message, onConfirm) {
    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    modal.innerHTML = `
        <div class="confirm-content">
            <div class="confirm-icon">🗑️</div>
            <h3>${title}</h3>
            <p>${message}</p>
            <div class="confirm-buttons">
                <button class="confirm-btn confirm-btn-cancel">İptal</button>
                <button class="confirm-btn confirm-btn-delete">Sil</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    modal.querySelector('.confirm-btn-cancel').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    modal.querySelector('.confirm-btn-delete').addEventListener('click', () => {
        document.body.removeChild(modal);
        onConfirm();
    });
}
```

---

