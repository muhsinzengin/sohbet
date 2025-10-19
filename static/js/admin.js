// ============================================
// SECURITY UTILITIES
// ============================================
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;')
        .replace(/\//g, '&#x2F;');
}

function safeSetTextContent(element, text) {
    if (element && text !== null && text !== undefined) {
        element.textContent = text;
    }
}

// Socket.IO with production-ready configuration + CSRF protection
const socket = io({
    transports: ['websocket', 'polling'],  // Support both transports
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,  // Increased for cold starts
    timeout: 30000,  // 30 seconds for cold start
    upgrade: true,
    rememberUpgrade: true,
    extraHeaders: {
        'X-CSRFToken': getCsrfToken()
    }
});

// CSRF token alma fonksiyonu
function getCsrfToken() {
    const token = document.querySelector('meta[name=csrf-token]');
    return token ? token.getAttribute('content') : '';
}

let currentThreadId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let onlineThreads = new Set();
let onlineTimeouts = new Map();

// Socket connection logging
socket.on('connect', () => {
    console.log('✅ Socket.IO bağlandı!');
    socket.emit('admin_join');
});

socket.on('connect_error', (error) => {
    console.error('❌ Bağlantı hatası:', error.message);
    console.log('Bağlantı hatası, yeniden deneniyor...');
});

socket.on('disconnect', (reason) => {
    console.log('⚠️ Bağlantı kesildi:', reason);
    if (reason === 'io server disconnect') {
        // Server disconnected, reconnect manually
        socket.connect();
    }
});

socket.on('reconnect', (attemptNumber) => {
    console.log('✅ Yeniden bağlandı (deneme:', attemptNumber, ')');
    socket.emit('admin_join');
    loadThreads();
});

const chatPanel = document.getElementById('chat-panel');
const threadListEl = document.getElementById('thread-list');
const backBtn = document.getElementById('back-btn');

// Geri butonu
backBtn.addEventListener('click', () => {
    currentThreadId = null;
    selectedName.textContent = '';
    selectedThreadInfo.style.display = 'none';
    adminInput.style.display = 'none';
    messagesDiv.innerHTML = '';
    
    // Thread listesine dön
    chatPanel.classList.remove('fullscreen');
    threadListEl.classList.remove('hidden');
    
    loadThreads();
});

const threadsDiv = document.getElementById('threads');
const messagesDiv = document.getElementById('admin-messages');
const msgInput = document.getElementById('admin-msg-input');
const sendBtn = document.getElementById('admin-send-btn');
const imageBtn = document.getElementById('admin-image-btn');
const audioBtn = document.getElementById('admin-audio-btn');
const imageInput = document.getElementById('admin-image-input');
const selectedName = document.getElementById('selected-name');
const selectedThreadInfo = document.getElementById('selected-thread-info');
const adminInput = document.getElementById('admin-input');
const clearThreadBtn = document.getElementById('clear-thread-btn');
const clearAllBtn = document.getElementById('clear-all-btn');

// Load threads
loadThreads();

// Auto-refresh thread times every 30 seconds
setInterval(() => {
    loadThreads();
}, 30000);

// Socket events
socket.on('message_from_visitor', (data) => {
    setThreadOnline(data.thread_id);
    if (data.thread_id === currentThreadId) {
        addMessage(data, 'visitor');
    }
    loadThreads();
    playNotification();
});



socket.on('visitor_online', (data) => {
    setThreadOnline(data.thread_id);
    loadThreads();
});

socket.on('message_from_telegram', (data) => {
    if (data.thread_id === currentThreadId) {
        addMessage(data, 'admin');
    }
    loadThreads();
});

// New message notification
socket.on('new_message_notification', (data) => {
    // Only show notification if not currently viewing that thread
    if (data.thread_id !== currentThreadId) {
        showMessageNotification(data);
    }
});

// Helper function to manage online status
function setThreadOnline(threadId) {
    // Clear existing timeout
    if (onlineTimeouts.has(threadId)) {
        clearTimeout(onlineTimeouts.get(threadId));
    }
    
    // Set online
    onlineThreads.add(threadId);
    
    // Set new timeout to remove after 2 minutes
    const timeout = setTimeout(() => {
        onlineThreads.delete(threadId);
        onlineTimeouts.delete(threadId);
        loadThreads();
    }, 2 * 60 * 1000);
    
    onlineTimeouts.set(threadId, timeout);
}

// Load threads
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
        
        // Check if online
        const isOnline = onlineThreads.has(thread.id);
        
        // Format time
        let dateText = '';
        let timeText = '';
        let agoText = '';
        let dateClass = 'online-text';
        
        if (isOnline) {
            dateText = 'Çevrimiçi';
        } else {
            const lastTime = thread.last_message_time || thread.last_activity_at;
            if (lastTime) {
                try {
                    // Parse date - SQLite format: YYYY-MM-DD HH:MM:SS (already in Turkey time UTC+3)
                    let msgDate;
                    if (lastTime.includes('T')) {
                        msgDate = new Date(lastTime);
                    } else {
                        // SQLite format - already in Turkey time
                        msgDate = new Date(lastTime.replace(' ', 'T'));
                    }
                    
                    // Format: DD.MM.YYYY
                    dateText = msgDate.toLocaleDateString('tr-TR', { 
                        day: '2-digit', 
                        month: '2-digit', 
                        year: 'numeric' 
                    });
                    
                    // Format: HH:MM
                    timeText = msgDate.toLocaleTimeString('tr-TR', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    });
                    
                    // Calculate "ago" text and time class
                    const now = new Date();
                    const diffMs = now - msgDate;
                    const diffMins = Math.floor(diffMs / 60000);
                    const diffHours = Math.floor(diffMs / 3600000);
                    const diffDays = Math.floor(diffMs / 86400000);
                    
                    let timeClass = '';
                    if (diffMins < 1) {
                        agoText = 'Şimdi';
                        timeClass = 'time-now';
                    } else if (diffMins < 60) {
                        agoText = diffMins + 'dk önce';
                        timeClass = 'time-minutes';
                    } else if (diffHours < 24) {
                        agoText = diffHours + 'sa önce';
                        timeClass = 'time-hours';
                    } else if (diffDays === 1) {
                        agoText = 'Dün';
                        timeClass = 'time-yesterday';
                    } else if (diffDays < 7) {
                        agoText = diffDays + 'g önce';
                        timeClass = 'time-days';
                    } else {
                        agoText = msgDate.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
                        timeClass = 'time-old';
                    }
                    div.setAttribute('data-time-class', timeClass);
                } catch (e) {
                    console.log('Date parse error:', e, lastTime);
                    dateText = '';
                    timeText = '';
                    agoText = '';
                }
            }
        }
        
        const timeClass = div.getAttribute('data-time-class') || '';
        
        // Renk ataması: Şimdi ve dakikalar için time, saatler için date
        let timeClass2 = '';
        if (!isOnline) {
            dateClass = '';
            if (timeClass === 'time-now') {
                timeClass2 = 'time-now'; // Yeşil
            } else if (timeClass === 'time-minutes') {
                timeClass2 = 'time-minutes'; // Mavi
            } else if (timeClass === 'time-hours') {
                dateClass = 'time-hours'; // Kırmızı
            }
        }
        
        // Create elements safely to prevent XSS
        const statusDot = document.createElement('div');
        statusDot.className = `status-dot ${isOnline ? 'online' : 'offline'}`;
        
        const threadContent = document.createElement('div');
        threadContent.className = 'thread-content';
        
        const threadRow1 = document.createElement('div');
        threadRow1.className = 'thread-row';
        
        const threadName = document.createElement('div');
        threadName.className = 'thread-name';
        threadName.textContent = thread.display_name; // Safe text content
        
        const threadRow2 = document.createElement('div');
        threadRow2.className = 'thread-row';
        
        const threadPreview = document.createElement('div');
        threadPreview.className = 'thread-preview';
        threadPreview.textContent = thread.last_message || 'Mesaj yok'; // Safe text content
        
        const dateTimeDiv = document.createElement('div');
        dateTimeDiv.className = 'thread-date-time';
        
        const dateSpan = document.createElement('span');
        dateSpan.className = `thread-date ${dateClass}`;
        dateSpan.textContent = dateText; // Safe text content
        
        // Assemble the structure
        threadRow1.appendChild(threadName);
        if (agoText) {
            const agoDiv = document.createElement('div');
            agoDiv.className = `thread-ago ${timeClass}`;
            agoDiv.textContent = agoText; // Safe text content
            threadRow1.appendChild(agoDiv);
        }
        
        threadRow2.appendChild(threadPreview);
        
        dateTimeDiv.appendChild(dateSpan);
        if (timeText) {
            const timeSpan = document.createElement('span');
            timeSpan.className = `thread-time ${timeClass2}`;
            timeSpan.textContent = timeText; // Safe text content
            dateTimeDiv.appendChild(timeSpan);
        }
        
        threadRow2.appendChild(dateTimeDiv);
        
        threadContent.appendChild(threadRow1);
        threadContent.appendChild(threadRow2);
        
        div.appendChild(statusDot);
        div.appendChild(threadContent);
        
        div.addEventListener('click', () => selectThread(thread.id, thread.display_name));
        threadsDiv.appendChild(div);
    });
}

// Select thread
async function selectThread(threadId, name) {
    currentThreadId = threadId;
    selectedName.textContent = name;
    selectedThreadInfo.style.display = 'flex';
    adminInput.style.display = 'flex';
    
    // Tam ekran modu (mobil-first)
    chatPanel.classList.add('fullscreen');
    threadListEl.classList.add('hidden');
    
    const res = await fetch(`/api/messages?thread_id=${threadId}`);
    const messages = await res.json();
    
    messagesDiv.innerHTML = '';
    messages.forEach(msg => {
        const senderClass = msg.sender === 'visitor' ? 'visitor' : 'admin';
        addMessage(msg, senderClass);
    });
    
    loadThreads();
}

// Send message
sendBtn.addEventListener('click', sendMessage);
msgInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || !currentThreadId) return;

    const msgData = {
        thread_id: currentThreadId,
        type: 'text',
        text: text
    };

    socket.emit('message_to_visitor', msgData);
    const now = new Date();
    addMessage({...msgData, content_text: text, sender: 'admin', created_at: now.toISOString()}, 'admin');
    msgInput.value = '';
}

// Image upload
imageBtn.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file || !currentThreadId) return;

    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch('/api/upload/image', {
        method: 'POST',
        body: formData
    });

    const data = await res.json();
    if (data.url) {
        const msgData = {
            thread_id: currentThreadId,
            type: 'image',
            file_url: data.url
        };
        socket.emit('message_to_visitor', msgData);
        const now = new Date();
        addMessage({...msgData, file_path: data.url, sender: 'admin', created_at: now.toISOString()}, 'admin');
    }
    imageInput.value = '';
});

// Audio recording
audioBtn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (!currentThreadId) return;

    if (!isRecording) {
        try {
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
                        thread_id: currentThreadId,
                        type: 'audio',
                        file_url: data.url
                    };
                    socket.emit('message_to_visitor', msgData);
                    const now = new Date();
                    addMessage({...msgData, file_path: data.url, sender: 'admin', created_at: now.toISOString()}, 'admin');
                }

                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            audioBtn.classList.add('recording');
            audioBtn.textContent = '⏹️';
        } catch (err) {
            alert('Mikrofon erişimi reddedildi');
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        audioBtn.classList.remove('recording');
        audioBtn.textContent = '🎤';
    }
}

// Add message to UI
function addMessage(data, senderClass) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${senderClass || (data.sender === 'visitor' ? 'visitor' : 'admin')}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (data.type === 'text') {
        bubble.textContent = data.content_text || data.text;
    } else if (data.type === 'image') {
        const img = document.createElement('img');
        img.src = data.file_path || data.file_url;
        img.style.maxWidth = '100%';
        img.style.borderRadius = '15px';
        img.style.marginTop = '10px';
        bubble.appendChild(img);
    } else if (data.type === 'audio') {
        const audio = document.createElement('audio');
        audio.src = data.file_path || data.file_url;
        audio.controls = true;
        audio.style.maxWidth = '100%';
        audio.style.marginTop = '10px';
        bubble.appendChild(audio);
    }

    const time = document.createElement('div');
    time.className = 'message-time';
    const msgDate = parseMessageDate(data.created_at);
    try {
        time.textContent = msgDate.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        time.textContent = '';
    }

    bubble.appendChild(time);
    msgDiv.appendChild(bubble);
    // Use global messagesDiv that targets '#admin-messages'
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Custom confirm modal
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
    
    const cancelBtn = modal.querySelector('.confirm-btn-cancel');
    const deleteBtn = modal.querySelector('.confirm-btn-delete');
    
    cancelBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    deleteBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
        onConfirm();
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Clear thread
clearThreadBtn.addEventListener('click', () => {
    if (!currentThreadId) return;
    
    showConfirmModal(
        'Konuşmayı Sil',
        'Bu konuşmadaki tüm mesajları silmek istediğinize emin misiniz?',
        async () => {
            await fetch(`/api/messages/clear?thread_id=${currentThreadId}`, {method: 'POST'});
            messagesDiv.innerHTML = '';
            loadThreads();
        }
    );
});

// Clear all
clearAllBtn.addEventListener('click', () => {
    showConfirmModal(
        'Tüm Konuşmaları Sil',
        'TÜM konuşmaları ve mesajları kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz!',
        async () => {
            await fetch('/api/messages/clear_all', {method: 'POST'});
            messagesDiv.innerHTML = '';
            currentThreadId = null;
            selectedName.textContent = '';
            selectedThreadInfo.style.display = 'none';
            adminInput.style.display = 'none';
            loadThreads();
        }
    );
});

// Play notification
function playNotification() {
    // Notification sound disabled
}

// Show message notification
function showMessageNotification(data) {
    // Remove existing notification if any
    const existingNotification = document.querySelector('.message-notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create notification element safely
    const notification = document.createElement('div');
    notification.className = 'message-notification';
    
    const notificationContent = document.createElement('div');
    notificationContent.className = 'notification-content';
    
    const notificationIcon = document.createElement('div');
    notificationIcon.className = 'notification-icon';
    notificationIcon.textContent = '💬';
    
    const notificationText = document.createElement('div');
    notificationText.className = 'notification-text';
    
    const notificationName = document.createElement('div');
    notificationName.className = 'notification-name';
    notificationName.textContent = data.display_name; // Safe text content
    
    const notificationPreview = document.createElement('div');
    notificationPreview.className = 'notification-preview';
    notificationPreview.textContent = data.message_preview; // Safe text content
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'notification-close';
    closeBtn.textContent = '×';
    
    notificationText.appendChild(notificationName);
    notificationText.appendChild(notificationPreview);
    
    notificationContent.appendChild(notificationIcon);
    notificationContent.appendChild(notificationText);
    notificationContent.appendChild(closeBtn);
    
    notification.appendChild(notificationContent);

    // Add to page
    document.body.appendChild(notification);

    // Show animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto hide after 5 seconds
    const hideTimeout = setTimeout(() => {
        hideNotification(notification);
    }, 5000);

    // Click to go to thread
    notification.addEventListener('click', (e) => {
        if (!e.target.classList.contains('notification-close')) {
            clearTimeout(hideTimeout);
            hideNotification(notification);
            selectThread(data.thread_id, data.display_name);
        }
    });

    // Close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        clearTimeout(hideTimeout);
        hideNotification(notification);
    });
}

function hideNotification(notification) {
    notification.classList.remove('show');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}

function parseMessageDate(input) {
    try {
        if (!input) return new Date();
        if (input instanceof Date) return input;
        if (typeof input === 'string') {
            let s = input.includes('T') ? input : input.replace(' ', 'T');
            let d = new Date(s);
            if (!isNaN(d.getTime())) return d;
            if (!s.endsWith('Z')) s += 'Z';
            d = new Date(s);
            if (!isNaN(d.getTime())) return d;
        }
    } catch (e) {}
    return new Date();
}

// ============================================
// ERROR HANDLING
// ============================================
socket.on('message_error', (data) => {
    console.error('Message error:', data);
    showNotification(data.message || 'Mesaj gönderilirken hata oluştu', 'error');
});

socket.on('connect_error', (error) => {
    console.error('❌ Bağlantı hatası:', error.message);
    showNotification('Sunucuya bağlanılamıyor. Yeniden deneniyor...', 'error');
});

socket.on('reconnect_failed', () => {
    showNotification('Sunucuya bağlanılamadı. Sayfayı yenileyin.', 'error');
});