// ============================================
// SAFE DOM LOADING
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM yüklendi, başlatılıyor...');
    initializeApp();
});

function initializeApp() {
    // ============================================
    // SOCKET.IO BAĞLANTISI
    // ============================================
    const socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 10,
        timeout: 30000,
        upgrade: true,
        rememberUpgrade: true
    });

    socket.on('connect', () => {
        console.log('✅ Socket.IO bağlandı!');
        console.log('🆔 Socket ID:', socket.id);
        isOnline = true;
    });

    socket.on('connect_error', (error) => {
        console.error('❌ Bağlantı hatası:', error.message);
        isOnline = false;
    });

    socket.on('disconnect', (reason) => {
        console.log('⚠️ Bağlantı kesildi:', reason);
        isOnline = false;
    });

    // ============================================
    // DOM ELEMENTS - MEVCUT YAPIYLA UYUMLU
    // ============================================
    
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
    const userName = document.getElementById('user-name');

    let threadId = null;
    let displayName = null;
    let inactivityTimer = null;
    let messageClearTimer = null;
    let heartbeatInterval = null;
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let isOnline = true;
    let messages = [];

    // Element kontrolü
    if (!joinBtn || !displayNameInput) {
        console.error('❌ Kritik elementler bulunamadı!');
        return;
    }

    console.log('✅ Tüm DOM elementleri bulundu!');

    // ============================================
    // JOIN BUTTON HANDLER
    // ============================================
    joinBtn.addEventListener('click', () => {
        displayName = displayNameInput.value.trim();
        console.log('👤 Join button clicked, name:', displayName);
        if (displayName) {
            console.log('📤 Emitting join event...');
            socket.emit('join', {display_name: displayName});
            
            nameModal.style.display = 'none';
            chatContainer.style.display = 'flex';
            userName.textContent = displayName;
            
            // Butonları kilitle - threadId gelene kadar
            sendBtn.disabled = true;
            msgInput.disabled = true;
            imageBtn.disabled = true;
            audioBtn.disabled = true;
            msgInput.placeholder = 'Bağlanıyor...';
            
            localStorage.setItem('chatSession', JSON.stringify({
                displayName: displayName,
                lastActivity: Date.now()
            }));
            
            resetInactivityTimer();
            startMessageClearTimer();
        }
    });

    if (displayNameInput) {
        displayNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') joinBtn.click();
        });
    }

    // ============================================
    // SOCKET EVENTS
    // ============================================
    socket.on('joined', (data) => {
        console.log('✅ Joined event:', data);
        threadId = data.thread_id;
        console.log('✅ threadId set:', threadId);
        
        // Butonları aktif et
        sendBtn.disabled = false;
        msgInput.disabled = false;
        imageBtn.disabled = false;
        audioBtn.disabled = false;
        msgInput.placeholder = 'Mesajınızı yazın...';
        
        // LocalStorage'a kaydet
        localStorage.setItem('chat_thread_id', threadId);
        localStorage.setItem('chat_display_name', displayName);
        
        startHeartbeat();
    });

    function startHeartbeat() {
        clearInterval(heartbeatInterval);
        heartbeatInterval = setInterval(() => {
            if (threadId) {
                socket.emit('heartbeat', { thread_id: threadId });
            }
        }, 30000);
    }

    function stopHeartbeat() {
        clearInterval(heartbeatInterval);
    }

    // Check existing session
    if (socket.connected) {
        checkExistingSession();
    }

    socket.on('connect', () => {
        checkExistingSession();
    });

    function checkExistingSession() {
        const savedThreadId = localStorage.getItem('chat_thread_id');
        const savedName = localStorage.getItem('chat_display_name');
        
        if (savedThreadId && savedName) {
            // Eski session'u kullan
            threadId = savedThreadId;
            displayName = savedName;
            
            nameModal.style.display = 'none';
            chatContainer.style.display = 'flex';
            userName.textContent = displayName;
            
            // Room'a tekrar join ol
            socket.emit('rejoin', {thread_id: threadId});
            startHeartbeat();
            resetInactivityTimer();
            startMessageClearTimer();
        }
    }

    socket.on('message_from_admin', (data) => {
        addMessage(data, 'admin');
        playNotification();
        resetInactivityTimer();
    });

    // ============================================
    // SEND MESSAGE
    // ============================================
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (msgInput) {
        msgInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    function sendMessage() {
        const text = msgInput.value.trim();
        
        console.log('📤 sendMessage çağrıldı:', { text, threadId });
        
        if (!text) {
            console.warn('⚠️ Mesaj boş!');
            return;
        }
        
        if (!threadId) {
            console.error('❌ threadId yok! Önce isim girip join yapmalısınız.');
            alert('Lütfen önce isminizi girin ve sohbete başlayın!');
            return;
        }

        const msgData = {
            thread_id: threadId,
            type: 'text',
            text: text
        };

        console.log('📨 Socket emit: message_to_admin', msgData);
        socket.emit('message_to_admin', msgData);
        // Use Turkey time for display
        const now = new Date();
        addMessage({...msgData, sender: 'visitor', created_at: now.toISOString()}, 'visitor');
        msgInput.value = '';
        resetInactivityTimer();
    }

    function addMessage(data, senderClass) {
        // Check for duplicate message
        if (messages.some(msg => msg.id === data.id)) {
            return;
        }

        // Add to messages array
        messages.push(data);

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${senderClass}`;

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
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // ============================================
    // IMAGE UPLOAD
    // ============================================
    if (imageBtn) imageBtn.addEventListener('click', () => imageInput.click());
    if (imageInput) {
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
            const now = new Date();
            addMessage({...msgData, sender: 'visitor', created_at: now.toISOString()}, 'visitor');
            resetInactivityTimer();
        }
            imageInput.value = '';
        });
    }

    // ============================================
    // AUDIO RECORDING
    // ============================================
    if (audioBtn) audioBtn.addEventListener('click', toggleRecording);

    async function toggleRecording() {
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
                            thread_id: threadId,
                            type: 'audio',
                            file_url: data.url
                        };
                        socket.emit('message_to_admin', msgData);
                        const now = new Date();
                        addMessage({...msgData, sender: 'visitor', created_at: now.toISOString()}, 'visitor');
                        resetInactivityTimer();
                    }

                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                isRecording = true;
                audioBtn.textContent = '⏹️';
                audioBtn.style.background = '#ef4444';
            } catch (error) {
                console.error('Mikrofon erişim hatası:', error);
                alert('Mikrofon erişimi reddedildi!');
            }
        } else {
            mediaRecorder.stop();
            isRecording = false;
            audioBtn.textContent = '🎤';
            audioBtn.style.background = '';
        }
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    function playNotification() {
        // Notification sound disabled
    }

    function parseMessageDate(input) {
        try {
            if (!input) return new Date();
            if (input instanceof Date) return input;
            if (typeof input === 'string') {
                // Normalize "YYYY-MM-DD HH:MM:SS" → "YYYY-MM-DDTHH:MM:SS"
                let s = input.includes('T') ? input : input.replace(' ', 'T');
                let d = new Date(s);
                if (!isNaN(d.getTime())) return d;
                // Fallback: try UTC assumption
                if (!s.endsWith('Z')) s += 'Z';
                d = new Date(s);
                if (!isNaN(d.getTime())) return d;
            }
        } catch (e) {}
        return new Date();
    }

    function resetInactivityTimer() {
        clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(() => {
            if (!isOnline) {
                localStorage.removeItem('chatSession');
                location.reload();
            }
        }, 2 * 60 * 1000);
    }

    function startMessageClearTimer() {
        clearTimeout(messageClearTimer);
        messageClearTimer = setTimeout(() => {
            messagesDiv.innerHTML = '';
        }, 5 * 60 * 1000);
    }

    console.log('✅ index.js başarıyla başlatıldı!');
}

// ============================================
// BİLDİRİM SİSTEMİ
// ============================================
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 10px;
        font-weight: bold;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    if (type === 'success') {
        notification.style.background = '#4CAF50';
        notification.style.color = '#FFF';
    } else {
        notification.style.background = '#F44336';
        notification.style.color = '#FFF';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Animasyonlar
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================
// THREE.JS BACKGROUND
// ============================================
if (typeof THREE !== 'undefined') {
    console.log('🎨 Three.js başlatılıyor...');
    
    try {
        const canvas = document.getElementById('canvas-bg');
        if (!canvas) {
            console.warn('⚠️ canvas-bg elementi bulunamadı');
        } else {
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setClearColor(0xf0f5fa, 0.1);

            camera.position.z = 50;

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
                sizeAttenuation: true,
                transparent: true,
                opacity: 0.4
            });

            const particles = new THREE.Points(particlesGeometry, particlesMaterial);
            scene.add(particles);

            function animate() {
                requestAnimationFrame(animate);
                particles.rotation.x += 0.0001;
                particles.rotation.y += 0.0002;

                const positionsArray = particlesGeometry.attributes.position.array;
                for (let i = 0; i < positionsArray.length; i += 3) {
                    positionsArray[i] += (Math.random() - 0.5) * 0.3;
                    positionsArray[i + 1] += (Math.random() - 0.5) * 0.3;
                }
                particlesGeometry.attributes.position.needsUpdate = true;

                renderer.render(scene, camera);
            }
            animate();

            window.addEventListener('resize', () => {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            });
            
            console.log('✅ Three.js animasyonu başlatıldı!');
        }
    } catch (error) {
        console.warn('⚠️ Three.js animasyonu başlatılamadı:', error);
    }
}
