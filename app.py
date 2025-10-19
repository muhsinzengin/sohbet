import os
import uuid
import asyncio
import random
import logging
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from config import Config
from database import db

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Session security
if Config.is_production():
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Production'da eventlet, development'da threading
if Config.is_production():
    # Production: Domain whitelist kullan
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode='eventlet')
else:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Telegram
telegram_bot = None
telegram_app = None
telegram_loop = None

if Config.TELEGRAM_BOT_TOKEN:
    from telegram import Bot, Update
    from telegram.ext import Application, MessageHandler, filters, ContextTypes
    # İsteğe bağlı: PTB hata tipleri (RetryAfter vb.)
    try:
        from telegram.error import RetryAfter
    except Exception:
        RetryAfter = None
    import threading
    
    telegram_bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    telegram_app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Telegram message handler with improved thread matching and media support
    async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
         if not update.message:
             return

         chat_id = str(update.message.chat.id)
         incoming_id = update.message.message_id

         # Handle media messages (photos, audio, documents)
         media_type = 'text'
         content_text = ''
         file_path = ''

         if update.message.photo:
             # Photo message
             media_type = 'image'
             # Get the largest photo size
             photo = update.message.photo[-1]
             file_info = await context.bot.get_file(photo.file_id)
             content_text = update.message.caption or ''
             file_path = file_info.file_path
         elif update.message.audio or update.message.voice:
             # Audio message
             media_type = 'audio'
             audio = update.message.audio or update.message.voice
             file_info = await context.bot.get_file(audio.file_id)
             content_text = update.message.caption or ''
             file_path = file_info.file_path
         elif update.message.document:
             # Document message
             media_type = 'file'
             file_info = await context.bot.get_file(update.message.document.file_id)
             content_text = update.message.caption or update.message.document.file_name or 'Dosya'
             file_path = file_info.file_path
         elif update.message.text:
             # Text message
             content_text = update.message.text.strip()
         else:
             # Unsupported message type
             return

         # Dedup: Bu Telegram mesajı daha önce işlendi mi?
         already = db.execute_query(
             'SELECT id FROM telegram_inbound WHERE tg_chat_id = ? AND tg_message_id = ?',
             (chat_id, incoming_id),
             fetch='one'
         )
         if already:
             logging.info(f"Telegram inbound duplicate skip: chat_id={chat_id}, msg_id={incoming_id}")
             return

         # Check if it's a reply to a previous message
         thread_id = None
         if update.message.reply_to_message:
             # Reply mesajı ise, orijinal mesajın thread_id'sini bul
             reply_to_id = update.message.reply_to_message.message_id
             link = db.execute_query(
                 'SELECT thread_id FROM telegram_links WHERE tg_message_id = ?',
                 (reply_to_id,),
                 fetch='one'
             )
             if link:
                 thread_id = link['thread_id']
                 logger.info(f"Reply detected, using thread_id: {thread_id}")

         # If no thread_id from reply, check for #thread: tag in message
         if not thread_id:
             thread_match = re.search(r'#thread:([a-f0-9\-]+)', content_text)
             if thread_match:
                 potential_thread_id = thread_match.group(1)
                 # Validate thread exists
                 thread_check = db.execute_query(
                     'SELECT id FROM threads WHERE id = ?',
                     (potential_thread_id,),
                     fetch='one'
                 )
                 if thread_check:
                     thread_id = potential_thread_id
                     logger.info(f"Thread tag found, using thread_id: {thread_id}")

         # If still no thread_id, this is a new message - create new thread
         if not thread_id:
             thread_id = str(uuid.uuid4())
             display_name = f"Telegram-{chat_id}"
             db.execute_query(
                 'INSERT INTO threads (id, display_name) VALUES (?, ?)',
                 (thread_id, display_name),
                 fetch=None
             )
             logger.info(f"New thread created for Telegram message: {thread_id}")

         # Save inbound message to prevent duplicates
         db.execute_query(
             'INSERT INTO telegram_inbound (tg_chat_id, tg_message_id) VALUES (?, ?)',
             (chat_id, incoming_id),
             fetch=None
         )

         # Save message to database (encrypt text content)
         msg_id = str(uuid.uuid4())
         encrypted_content = encrypt_message(content_text, ENCRYPTION_KEY) if content_text and media_type == 'text' else content_text
         db.execute_query(
             'INSERT INTO messages (id, thread_id, sender, type, content_text, file_path) VALUES (?, ?, ?, ?, ?, ?)',
             (msg_id, thread_id, 'telegram', media_type, encrypted_content, file_path),
             fetch=None
         )

         # Link Telegram message to thread for future replies
         db.execute_query(
             'INSERT INTO telegram_links (thread_id, tg_chat_id, tg_message_id) VALUES (?, ?, ?)',
             (thread_id, chat_id, incoming_id),
             fetch=None
         )

         # Emit to admin room and visitor room
         msg = db.execute_query('SELECT * FROM messages WHERE id = ?', (msg_id,), fetch='one')
         if msg and msg['content_text'] and msg['type'] == 'text':
             try:
                 msg['content_text'] = decrypt_message(msg['content_text'], ENCRYPTION_KEY)
             except Exception as e:
                 logger.warning(f"Failed to decrypt telegram message {msg_id}: {e}")

         # Send to admin room
         socketio.emit('message_from_telegram', msg, room='admin_room')
         # Send to visitor room (thread room) - Telegram mesajları için doğru event
         socketio.emit('message_from_telegram', msg, room=thread_id)

         logger.info(f"Telegram message processed: thread={thread_id}, msg_id={msg_id}, type={media_type}")
    
    # Add handlers for different message types
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_telegram_message))
    telegram_app.add_handler(MessageHandler(filters.AUDIO, handle_telegram_message))
    telegram_app.add_handler(MessageHandler(filters.VOICE, handle_telegram_message))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_telegram_message))
    
    # Retry/backoff ile güvenli gönderim yardımcı fonksiyonu
    async def send_telegram_with_retry(chat_id, text, thread_id=None, max_retries=3):
        delay_base = 0.75
        last_exc = None
        for attempt in range(max_retries):
            try:
                tg_msg = await telegram_bot.send_message(chat_id=chat_id, text=text)
                if thread_id:
                    try:
                        db.execute_query(
                            'INSERT INTO telegram_links (thread_id, tg_chat_id, tg_message_id) VALUES (?, ?, ?)',
                            (thread_id, str(tg_msg.chat_id), tg_msg.message_id),
                            fetch=None
                        )
                    except Exception as e:
                        logger.warning(f"telegram_links insert failed: {e}")
                logger.info(f"Telegram gönderimi başarılı: chat={tg_msg.chat_id}, msg_id={tg_msg.message_id}, attempt={attempt+1}")
                return tg_msg
            except Exception as e:
                last_exc = e
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    wait_s = float(retry_after)
                else:
                    jitter = random.uniform(0.2, 0.8)
                    wait_s = delay_base * (2 ** attempt) + jitter
                logger.warning(f"Telegram send attempt {attempt+1} failed: {e}. {wait_s:.2f}s sonra tekrar denenecek.")
                await asyncio.sleep(wait_s)
        logger.error(f"Telegram send failed after {max_retries} attempts: {last_exc}")
        raise last_exc
    
    # Start telegram bot in background thread with reconnect
    def start_telegram_bot():
        import asyncio
        global telegram_loop
        telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(telegram_loop)

        while True:
            try:
                logger.info('Telegram bot polling başlatılıyor...')
                # PTB v20: run_polling yönetir (initialize/start/idling)
                telegram_app.run_polling(stop_signals=None)
            except Exception as e:
                logger.error(f'Telegram bot bağlantı hatası: {e}')
                logger.info('30 saniye sonra yeniden bağlanmaya çalışılacak...')
                asyncio.sleep(30)  # Reconnect delay
            except KeyboardInterrupt:
                logger.info('Telegram bot durduruluyor...')
                break

    # Flask debug reloader ile çift instance oluşmasını engelle
    should_start_bot = Config.is_production() or (os.environ.get('WERKZEUG_RUN_MAIN') == 'true')
    if should_start_bot:
        telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        telegram_thread.start()
        logger.info('Telegram bot started with reconnect capability')
    else:
        logger.info('Telegram bot init deferred due to Flask reloader')
else:
    logger.info('Telegram bot disabled (no token)')
    telegram_app = None

# Cloudinary
cloudinary_configured = False
if Config.is_production() and Config.CLOUDINARY_CLOUD_NAME:
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET
        )
        cloudinary_configured = True
    except:
        pass

# Encryption utilities
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Generate encryption key from password
def get_encryption_key(password: str, salt: bytes = None) -> bytes:
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

# Encrypt/decrypt functions
def encrypt_message(text: str, key: bytes) -> str:
    f = Fernet(key)
    encrypted = f.encrypt(text.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_message(encrypted_text: str, key: bytes) -> str:
    f = Fernet(key)
    decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_text))
    return decrypted.decode()

# Global encryption key (should be from config in production)
ENCRYPTION_KEY = get_encryption_key(Config.SECRET_KEY)

# Rate limiting for uploads and messages
upload_rate_limit = {}
message_rate_limit = {}

def check_rate_limit(user_key, limit_store, max_requests=10, window_seconds=60):
    """Rate limiting kontrolü"""
    now = datetime.now().timestamp()
    if user_key not in limit_store:
        limit_store[user_key] = []

    # Eski istekleri temizle
    limit_store[user_key] = [t for t in limit_store[user_key] if now - t < window_seconds]

    if len(limit_store[user_key]) >= max_requests:
        return False

    limit_store[user_key].append(now)
    return True

# OTP'yi database'e kaydetmek için yardımcı fonksiyon
def save_otp_to_db(otp_code, expires_at):
    """OTP'yi database'e kaydet (production için)"""
    try:
        db.execute_query(
            'INSERT INTO otp_codes (code, expires_at) VALUES (?, ?)',
            (otp_code, expires_at),
            fetch=None
        )
        return True
    except Exception as e:
        logger.error(f"OTP DB save failed: {e}")
        return False

def get_otp_from_db(otp_code):
    """OTP'yi database'den al"""
    try:
        result = db.execute_query(
            'SELECT * FROM otp_codes WHERE code = ? AND expires_at > ?',
            (otp_code, db.get_current_timestamp()),
            fetch='one'
        )
        return result
    except Exception as e:
        logger.error(f"OTP DB get failed: {e}")
        return None

def delete_otp_from_db(otp_code):
    """OTP'yi database'den sil"""
    try:
        db.execute_query(
            'DELETE FROM otp_codes WHERE code = ?',
            (otp_code,),
            fetch=None
        )
    except Exception as e:
        logger.error(f"OTP DB delete failed: {e}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/request-otp', methods=['POST'])
def request_otp():
    # Token validasyonu
    if not Config.TELEGRAM_BOT_TOKEN:
        return jsonify({'success': False, 'message': 'Telegram bot token bulunamadı'}), 500

    if not Config.TELEGRAM_CHAT_ID:
        return jsonify({'success': False, 'message': 'Telegram chat ID bulunamadı'}), 500

    otp = str(random.randint(100000, 999999))
    expires_at = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')

    # OTP'yi database'e kaydet
    if not save_otp_to_db(otp, expires_at):
        logger.error("OTP database'e kaydedilemedi")
        return jsonify({'success': False, 'message': 'OTP kaydedilemedi'}), 500

    if telegram_bot and Config.TELEGRAM_CHAT_ID and telegram_loop:
        try:
            async def send_otp():
                await send_telegram_with_retry(
                    Config.TELEGRAM_CHAT_ID,
                    f"🔐 Admin OTP Kodu: {otp}\n\n⏰ 5 dakika geçerli"
                )
            future = asyncio.run_coroutine_threadsafe(send_otp(), telegram_loop)

            # Future'ın sonucunu kontrol et
            def handle_result(fut):
                try:
                    fut.result()  # Hata varsa exception raise eder
                    logger.info("OTP Telegram'a başarıyla gönderildi")
                except Exception as e:
                    logger.error(f'OTP Telegram gönderimi başarısız: {e}')

            future.add_done_callback(handle_result)
            return jsonify({'success': True, 'message': "OTP Telegram'a gönderildi"})
        except Exception as e:
            logger.error(f'Telegram error: {e}')
            return jsonify({'success': True, 'otp': otp, 'message': f'Test OTP: {otp}'})
    else:
        # Development mode - show OTP in response
        return jsonify({'success': True, 'otp': otp, 'message': f'Test OTP: {otp}'})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    otp = data.get('otp', '')

    # OTP'yi database'den al
    stored = get_otp_from_db(otp)
    if not stored:
        return jsonify({'success': False, 'message': 'Geçersiz veya süresi dolmuş OTP'})

    # OTP'yi kullan ve sil
    delete_otp_from_db(otp)
    session['admin'] = True
    return jsonify({'success': True, 'redirect': '/admin'})

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/api/threads')
def get_threads():
    if not session.get('admin'):
        return jsonify([]), 401
    
    if db.is_postgres:
        order_clause = 'ORDER BY last_message_time DESC NULLS LAST'
    else:
        order_clause = 'ORDER BY COALESCE(last_message_time, created_at) DESC'
    
    threads = db.execute_query(f'''
        SELECT t.*, 
               (SELECT content_text FROM messages WHERE thread_id = t.id ORDER BY created_at DESC LIMIT 1) as last_message,
               (SELECT created_at FROM messages WHERE thread_id = t.id ORDER BY created_at DESC LIMIT 1) as last_message_time
        FROM threads t
        {order_clause}
    ''')
    return jsonify(threads)

@app.route('/api/messages')
def get_messages():
    if not session.get('admin'):
        return jsonify([]), 401

    thread_id = request.args.get('thread_id')
    messages = db.execute_query(
        'SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC',
        (thread_id,)
    )

    # Decrypt text messages for admin view
    for msg in messages:
        if msg['content_text'] and msg['type'] == 'text':
            try:
                msg['content_text'] = decrypt_message(msg['content_text'], ENCRYPTION_KEY)
            except Exception as e:
                logger.warning(f"Failed to decrypt message {msg['id']}: {e}")
                msg['content_text'] = "[Şifrelenmiş mesaj okunamıyor]"

    return jsonify(messages)

@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    # Rate limiting kontrolü
    client_ip = request.remote_addr
    if not check_rate_limit(f"upload_{client_ip}", upload_rate_limit, max_requests=5, window_seconds=300):
        return jsonify({'error': 'Çok fazla yükleme isteği. Lütfen 5 dakika bekleyin.'}), 429

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Dosya bulunamadı'}), 400

    # Content type validation
    if not file.content_type or not file.content_type.startswith('image/'):
        return jsonify({'error': 'Geçersiz dosya tipi. Sadece resim dosyaları kabul edilir'}), 400

    # File size limit (5MB)
    if file.content_length and file.content_length > 5 * 1024 * 1024:
        return jsonify({'error': 'Dosya çok büyük. Maksimum 5MB'}), 400

    try:
        if cloudinary_configured:
            # Orijinal kaliteyi koru - quality=100, format=auto, no compression
            result = cloudinary.uploader.upload(file, folder='chat_images',
                                              quality=100,
                                              format='auto',
                                              flags='lossy')
            return jsonify({'url': result['secure_url']})
        else:
            os.makedirs('uploads/images', exist_ok=True)
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename or 'image.jpg')}"
            path = os.path.join('uploads/images', filename)
            file.save(path)
            return jsonify({'url': f'/uploads/images/{filename}'})
    except Exception as e:
        logger.error(f'Image upload failed: {e}')
        return jsonify({'error': f'Yükleme başarısız: {str(e)}'}), 500

@app.route('/api/upload/audio', methods=['POST'])
def upload_audio():
    # Rate limiting kontrolü
    client_ip = request.remote_addr
    if not check_rate_limit(f"upload_{client_ip}", upload_rate_limit, max_requests=3, window_seconds=300):
        return jsonify({'error': 'Çok fazla yükleme isteği. Lütfen 5 dakika bekleyin.'}), 429

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Dosya bulunamadı'}), 400

    # Content type validation
    allowed_types = ['audio/webm', 'audio/ogg', 'audio/wav', 'audio/mp3', 'audio/mpeg']
    if not file.content_type or file.content_type not in allowed_types:
        return jsonify({'error': 'Geçersiz dosya tipi. Sadece ses dosyaları kabul edilir'}), 400

    # File size limit (10MB for audio)
    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return jsonify({'error': 'Dosya çok büyük. Maksimum 10MB'}), 400

    try:
        if cloudinary_configured:
            # Orijinal kaliteyi koru - quality=100, format=auto, no compression
            result = cloudinary.uploader.upload(file, folder='chat_audio',
                                              resource_type='video',
                                              quality=100,
                                              format='auto',
                                              flags='lossy')
            return jsonify({'url': result['secure_url']})
        else:
            os.makedirs('uploads/audio', exist_ok=True)
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename or 'audio.webm')}"
            path = os.path.join('uploads/audio', filename)
            file.save(path)
            return jsonify({'url': f'/uploads/audio/{filename}'})
    except Exception as e:
        logger.error(f'Audio upload failed: {e}')
        return jsonify({'error': f'Yükleme başarısız: {str(e)}'}), 500

@app.route('/uploads/<folder>/<filename>')
def serve_upload(folder, filename):
    from flask import send_from_directory

    # Path traversal koruması - sadece izin verilen klasörler
    allowed_folders = ['images', 'audio']
    if folder not in allowed_folders:
        return jsonify({'error': 'Invalid folder'}), 403

    # Güvenli path kontrolü
    safe_path = os.path.join('uploads', folder)
    if not os.path.abspath(safe_path).startswith(os.path.abspath('uploads')):
        return jsonify({'error': 'Invalid path'}), 403

    return send_from_directory(safe_path, filename)

@app.route('/api/messages/clear', methods=['POST'])
def clear_thread():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    thread_id = request.args.get('thread_id')
    db.execute_query('DELETE FROM messages WHERE thread_id = ?', (thread_id,), fetch=None)
    db.execute_query('DELETE FROM telegram_links WHERE thread_id = ?', (thread_id,), fetch=None)
    return jsonify({'success': True})

@app.route('/api/messages/clear_all', methods=['POST'])
def clear_all():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    db.execute_query('DELETE FROM messages', fetch=None)
    db.execute_query('DELETE FROM threads', fetch=None)
    db.execute_query('DELETE FROM telegram_links', fetch=None)
    db.execute_query('DELETE FROM telegram_inbound', fetch=None)
    return jsonify({'success': True})



# Socket.IO
@socketio.on('join')
def handle_join(data):
    thread_id = str(uuid.uuid4())
    display_name = data.get('display_name', 'Ziyaretçi')
    
    db.execute_query(
        'INSERT INTO threads (id, display_name) VALUES (?, ?)',
        (thread_id, display_name),
        fetch=None
    )
    
    join_room(thread_id)
    emit('joined', {'thread_id': thread_id})

@socketio.on('rejoin')
def handle_rejoin(data):
    thread_id = data.get('thread_id')
    if thread_id:
        # Thread var mı kontrol et
        thread = db.execute_query(
            'SELECT id FROM threads WHERE id = ?',
            (thread_id,),
            fetch='one'
        )
        if thread:
            join_room(thread_id)
            emit('joined', {'thread_id': thread_id})
        else:
            # Thread bulunamadı - session'ı temizle
            logger.warning(f"Thread bulunamadı, session temizleniyor: {thread_id}")
            emit('rejoin_failed', {
                'message': 'Konuşma bulunamadı, yeni konuşma başlatılıyor',
                'thread_id': thread_id
            })

@socketio.on('admin_join')
def handle_admin_join():
    join_room('admin_room')

@socketio.on('heartbeat')
def handle_heartbeat(data):
    thread_id = data.get('thread_id')
    if thread_id:
        current_time = db.get_current_timestamp()
        db.execute_query(
            "UPDATE threads SET last_activity_at = ? WHERE id = ?",
            (current_time, thread_id),
            fetch=None
        )
        emit('visitor_online', {'thread_id': thread_id}, room='admin_room')

@socketio.on('message_to_admin')
def handle_message_to_admin(data):
    # Rate limiting kontrolü
    client_ip = request.remote_addr
    if not check_rate_limit(f"message_{client_ip}", message_rate_limit, max_requests=20, window_seconds=60):
        emit('message_error', {
            'type': 'rate_limit_exceeded',
            'message': 'Çok fazla mesaj gönderiyorsunuz. Lütfen biraz bekleyin.'
        }, room=data.get('thread_id'))
        return

    thread_id = data.get('thread_id')
    msg_type = data.get('type', 'text')

    msg_id = str(uuid.uuid4())
    content_text = data.get('text', '')
    file_path = data.get('file_url', '')

    try:
        # Encrypt message content if it's text
        encrypted_content = encrypt_message(content_text, ENCRYPTION_KEY) if content_text and msg_type == 'text' else content_text

        db.execute_query(
            'INSERT INTO messages (id, thread_id, sender, type, content_text, file_path) VALUES (?, ?, ?, ?, ?, ?)',
            (msg_id, thread_id, 'visitor', msg_type, encrypted_content, file_path),
            fetch=None
        )

        # Decrypt for sending to admin
        msg = db.execute_query('SELECT * FROM messages WHERE id = ?', (msg_id,), fetch='one')
        if msg and msg['content_text'] and msg['type'] == 'text':
            msg['content_text'] = decrypt_message(msg['content_text'], ENCRYPTION_KEY)

        emit('message_from_visitor', msg, room='admin_room')

        # Send notification to admin about new message
        thread = db.execute_query('SELECT display_name FROM threads WHERE id = ?', (thread_id,), fetch='one')
        if thread:
            # Create message preview (first 50 characters)
            message_preview = content_text[:50] + ('...' if len(content_text) > 50 else '') if content_text else 'Medya mesajı'

            emit('new_message_notification', {
                'thread_id': thread_id,
                'display_name': thread['display_name'],
                'message_preview': message_preview,
                'timestamp': db.get_current_timestamp()
            }, room='admin_room')

        if telegram_bot and Config.TELEGRAM_CHAT_ID and msg_type == 'text' and telegram_loop:
            thread = db.execute_query('SELECT display_name FROM threads WHERE id = ?', (thread_id,), fetch='one')
            if thread:
                try:
                    async def send_telegram():
                        text = f"💬 {thread['display_name']}\n\n{content_text}\n\n#thread:{thread_id}"
                        await send_telegram_with_retry(Config.TELEGRAM_CHAT_ID, text, thread_id=thread_id, max_retries=3)
                    future = asyncio.run_coroutine_threadsafe(send_telegram(), telegram_loop)

                    # Future sonucunu kontrol et
                    def handle_telegram_result(fut):
                        try:
                            fut.result()
                            logger.info(f"Telegram mesajı başarıyla gönderildi: thread_id={thread_id}")
                        except Exception as e:
                            logger.error(f"Telegram mesajı gönderilemedi: {e}")
                            # Kullanıcıya hata bildirimi gönder
                            emit('message_error', {
                                'type': 'telegram_send_failed',
                                'message': 'Telegram bildirimi gönderilemedi'
                            }, room=thread_id)

                    future.add_done_callback(handle_telegram_result)
                except Exception as e:
                    logger.error(f'Telegram send error: {e}')
    except Exception as e:
        logger.error(f"Message save error: {e}")
        # DB hatası durumunda kullanıcıya bildir
        emit('message_error', {
            'type': 'db_save_failed',
            'message': 'Mesaj kaydedilemedi'
        }, room=thread_id)

@socketio.on('message_to_visitor')
def handle_message_to_visitor(data):
    thread_id = data.get('thread_id')
    msg_type = data.get('type', 'text')

    msg_id = str(uuid.uuid4())
    content_text = data.get('text', '')
    file_path = data.get('file_url', '')

    try:
        # Encrypt message content if it's text
        encrypted_content = encrypt_message(content_text, ENCRYPTION_KEY) if content_text and msg_type == 'text' else content_text

        db.execute_query(
            'INSERT INTO messages (id, thread_id, sender, type, content_text, file_path) VALUES (?, ?, ?, ?, ?, ?)',
            (msg_id, thread_id, 'admin', msg_type, encrypted_content, file_path),
            fetch=None
        )

        # Decrypt for sending to visitor
        msg = db.execute_query('SELECT * FROM messages WHERE id = ?', (msg_id,), fetch='one')
        if msg and msg['content_text'] and msg['type'] == 'text':
            msg['content_text'] = decrypt_message(msg['content_text'], ENCRYPTION_KEY)

        emit('message_from_admin', msg, room=thread_id)
        emit('message_from_telegram', msg, room='admin_room', include_self=False)
    except Exception as e:
        logger.error(f"Admin message save error: {e}")
        # DB hatası durumunda kullanıcıya bildir
        emit('message_error', {
            'type': 'db_save_failed',
            'message': 'Mesaj kaydedilemedi'
        }, room='admin_room')

# Uygulama ilk HTTP isteğinde DB şemasını garanti et
@app.before_request
def ensure_db_initialized():
    if not hasattr(app, '_db_initialized'):
        try:
            db.init_db()
            logger.info('Database initialized (before_request)')
            app._db_initialized = True
        except Exception as e:
            logger.error(f'DB init failed: {e}')

if __name__ == '__main__':
    db.init_db()
    logger.info('Database initialized')
    logger.info('Server starting on http://localhost:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
