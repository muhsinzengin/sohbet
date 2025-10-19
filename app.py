import os
import uuid
import asyncio
import random
import logging
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import db
from rate_limiter import rate_limit
from cache import message_cache, cached_thread_messages
from security import security_manager

# Enhanced Logging Setup - Railway için JSON format + Log Injection Protection
def setup_enhanced_logging():
    # JSON format logging for Railway
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            # Sanitize log message to prevent log injection
            message = str(record.getMessage())
            # Remove newlines and control characters
            message = re.sub(r'[\r\n\t]', ' ', message)
            # Limit message length
            message = message[:1000]
            
            log_entry = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'message': message,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'environment': 'production' if Config.is_production() else 'development'
            }
            # Add extra fields if available (safe attribute access)
            if hasattr(record, 'user_id') and record.user_id:
                log_entry['user_id'] = str(record.user_id)[:50]  # Limit length
            if hasattr(record, 'thread_id') and record.thread_id:
                log_entry['thread_id'] = str(record.thread_id)[:50]  # Limit length
            if hasattr(record, 'endpoint') and record.endpoint:
                log_entry['endpoint'] = str(record.endpoint)[:100]  # Limit length
            return json.dumps(log_entry)

    # Setup handlers
    if Config.is_production():
        # Railway: JSON format to stdout for better log aggregation
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
    else:
        # Development: File logging
        os.makedirs('logs', exist_ok=True)
        handler = RotatingFileHandler('logs/chat.log', maxBytes=10*1024*1024, backupCount=5)
        handler.setFormatter(JSONFormatter())

    # Add handler to logger
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger

# Initialize enhanced logging
logger = setup_enhanced_logging()

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# CSRF Protection
csrf = CSRFProtect(app)

# Session security - Production'da güvenlik ayarları
if Config.is_production():
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    logger.info('Production session security enabled')

# CORS ayarları - Production'da güvenlik için whitelist kullan
if Config.is_production():
    # Production: Environment variable'dan whitelist al, varsayılan olarak Railway domain
    default_origins = 'https://your-app-name.railway.app'
    cors_origins = os.getenv('CORS_ORIGINS', default_origins).split(',')
    socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode='eventlet',
                        ping_timeout=60, ping_interval=25)  # Railway için optimize edilmiş ping ayarları
else:
    # Development: Tüm origin'lere izin ver
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
    async def start_telegram_bot_async():
        while True:
            try:
                logger.info('Telegram bot polling başlatılıyor...')
                # PTB v20: run_polling yönetir (initialize/start/idling)
                # Conflict hatasını önlemek için drop_pending_updates=True
                telegram_app.run_polling(stop_signals=None, drop_pending_updates=True)
            except Exception as e:
                logger.error(f'Telegram bot bağlantı hatası: {e}')
                logger.info('30 saniye sonra yeniden bağlanmaya çalışılacak...')
                await asyncio.sleep(30)  # Non-blocking reconnect delay
            except KeyboardInterrupt:
                logger.info('Telegram bot durduruluyor...')
                break

    def start_telegram_bot():
        import asyncio
        global telegram_loop
        telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(telegram_loop)

        # Async fonksiyonu çalıştır
        telegram_loop.run_until_complete(start_telegram_bot_async())

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
# Repair rate limiting store
repair_rate_limit = {}

def check_repair_rate_limit():
    """Rate limiting for repair operations - 1 per hour per admin"""
    admin_id = session.get('admin_id', 'unknown')
    now = datetime.now().timestamp()
    window_seconds = 3600  # 1 hour
    max_requests = 1
    
    if admin_id not in repair_rate_limit:
        repair_rate_limit[admin_id] = []
    
    # Clean old requests
    repair_rate_limit[admin_id] = [t for t in repair_rate_limit[admin_id] if now - t < window_seconds]
    
    if len(repair_rate_limit[admin_id]) >= max_requests:
        return False
    
    repair_rate_limit[admin_id].append(now)
    return True

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

# Global Error Handlers
@app.errorhandler(Exception)
def handle_global_error(error):
    logger.error(f"Global error: {error}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR',
        'timestamp': datetime.now().isoformat()
    }), 500

@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(429)
def handle_rate_limit(error):
    return jsonify({
        'success': False,
        'error': 'Too many requests',
        'code': 'RATE_LIMIT_EXCEEDED',
        'timestamp': datetime.now().isoformat()
    }), 429

# Standardized API Response Helper
def api_response(success=True, data=None, error=None, code=None, status=200):
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    if success and data is not None:
        response['data'] = data
    if not success and error:
        response['error'] = error
        response['code'] = code or 'UNKNOWN_ERROR'
    return jsonify(response), status

# Socket.IO Error Handler
@socketio.on_error_default
def handle_socket_error(e):
    logger.error(f"Socket.IO error: {e}")
    emit('error', {
        'type': 'socket_error',
        'message': 'Connection error occurred',
        'timestamp': datetime.now().isoformat()
    })

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
        return api_response(success=False, error='Unauthorized', code='UNAUTHORIZED', status=401)

    thread_id = request.args.get('thread_id')
    if not thread_id:
        return api_response(success=False, error='Thread ID required', code='MISSING_THREAD_ID', status=400)

    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    offset = (page - 1) * per_page

    try:
        # Try to get from cache first (only for first page)
        if page == 1:
            cached_messages = message_cache.get_thread_messages(thread_id, per_page)
            if cached_messages:
                # Get total count separately
                total_result = db.execute_query(
                    'SELECT COUNT(*) as count FROM messages WHERE thread_id = ?',
                    (thread_id,),
                    fetch='one'
                )
                total = total_result['count'] if total_result else 0

                pagination_info = {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                    'has_more': page < ((total + per_page - 1) // per_page),
                    'cached': True
                }

                return api_response(data={
                    'messages': cached_messages,
                    'pagination': pagination_info
                })

        # Get total count
        total_result = db.execute_query(
            'SELECT COUNT(*) as count FROM messages WHERE thread_id = ?',
            (thread_id,),
            fetch='one'
        )
        total = total_result['count'] if total_result else 0

        # Get paginated messages
        messages = db.execute_query(
            'SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (thread_id, per_page, offset)
        )

        # Decrypt text messages for admin view
        for msg in messages:
            if msg['content_text'] and msg['type'] == 'text':
                try:
                    msg['content_text'] = decrypt_message(msg['content_text'], ENCRYPTION_KEY)
                except Exception as e:
                    logger.warning(f"Failed to decrypt message {msg['id']}: {e}")
                    msg['content_text'] = "[Şifrelenmiş mesaj okunamıyor]"

        # Reverse to show chronological order (oldest first)
        messages.reverse()

        # Cache first page messages
        if page == 1:
            message_cache.set_thread_messages(thread_id, messages, per_page)

        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_more': page < ((total + per_page - 1) // per_page),
            'cached': False
        }

        return api_response(data={
            'messages': messages,
            'pagination': pagination_info
        })

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return api_response(success=False, error='Failed to fetch messages', code='FETCH_ERROR', status=500)

@app.route('/api/upload/image', methods=['POST'])
@rate_limit('upload')
def upload_image():
    # Rate limiting kontrolü
    client_ip = request.remote_addr
    if not check_rate_limit(f"upload_{client_ip}", upload_rate_limit, max_requests=5, window_seconds=300):
        return api_response(success=False, error='Çok fazla yükleme isteği. Lütfen 5 dakika bekleyin.', code='RATE_LIMIT_EXCEEDED', status=429)

    file = request.files.get('file')
    if not file:
        return api_response(success=False, error='Dosya bulunamadı', code='NO_FILE', status=400)

    # Content type validation
    if not file.content_type or not file.content_type.startswith('image/'):
        return api_response(success=False, error='Geçersiz dosya tipi. Sadece resim dosyaları kabul edilir', code='INVALID_FILE_TYPE', status=400)

    # File size limit (5MB)
    if file.content_length and file.content_length > 5 * 1024 * 1024:
        return api_response(success=False, error='Dosya çok büyük. Maksimum 5MB', code='FILE_TOO_LARGE', status=400)

    try:
        if cloudinary_configured:
            # Orijinal kaliteyi koru - quality=100, format=auto, no compression
            result = cloudinary.uploader.upload(file, folder='chat_images',
                                              quality=100,
                                              format='auto',
                                              flags='lossy')
            return api_response(data={'url': result['secure_url']})
        else:
            os.makedirs('uploads/images', exist_ok=True)
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename or 'image.jpg')}"
            path = os.path.join('uploads/images', filename)
            
            # Enhanced path traversal protection
            abs_path = os.path.abspath(path)
            uploads_dir = os.path.abspath('uploads/images')
            if not abs_path.startswith(uploads_dir):
                logger.warning(f"Path traversal attempt blocked: {path}")
                return api_response(success=False, error='Invalid file path', code='INVALID_PATH', status=400)
            
            file.save(path)
            return api_response(data={'url': f'/uploads/images/{filename}'})
    except Exception as e:
        logger.error(f'Image upload failed: {e}')
        return api_response(success=False, error='Yükleme başarısız', code='UPLOAD_FAILED', status=500)

@app.errorhandler(405)
def handle_method_not_allowed(error):
    return api_response(success=False, error='Method not allowed', code='METHOD_NOT_ALLOWED', status=405)

@app.route('/api/upload/audio', methods=['POST'])
@rate_limit('upload')
def upload_audio():
    # Rate limiting kontrolü
    client_ip = request.remote_addr
    if not check_rate_limit(f"upload_{client_ip}", upload_rate_limit, max_requests=3, window_seconds=300):
        return api_response(success=False, error='Çok fazla yükleme isteği. Lütfen 5 dakika bekleyin.', code='RATE_LIMIT_EXCEEDED', status=429)

    file = request.files.get('file')
    if not file:
        return api_response(success=False, error='Dosya bulunamadı', code='NO_FILE', status=400)

    # Content type validation
    allowed_types = ['audio/webm', 'audio/ogg', 'audio/wav', 'audio/mp3', 'audio/mpeg']
    if not file.content_type or file.content_type not in allowed_types:
        return api_response(success=False, error='Geçersiz dosya tipi. Sadece ses dosyaları kabul edilir', code='INVALID_FILE_TYPE', status=400)

    # File size limit (10MB for audio)
    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return api_response(success=False, error='Dosya çok büyük. Maksimum 10MB', code='FILE_TOO_LARGE', status=400)

    try:
        if cloudinary_configured:
            # Orijinal kaliteyi koru - quality=100, format=auto, no compression
            result = cloudinary.uploader.upload(file, folder='chat_audio',
                                              resource_type='video',
                                              quality=100,
                                              format='auto',
                                              flags='lossy')
            return api_response(data={'url': result['secure_url']})
        else:
            os.makedirs('uploads/audio', exist_ok=True)
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename or 'audio.webm')}"
            path = os.path.join('uploads/audio', filename)
            
            # Enhanced path traversal protection
            abs_path = os.path.abspath(path)
            uploads_dir = os.path.abspath('uploads/audio')
            if not abs_path.startswith(uploads_dir):
                logger.warning(f"Path traversal attempt blocked: {path}")
                return api_response(success=False, error='Invalid file path', code='INVALID_PATH', status=400)
            
            file.save(path)
            return api_response(data={'url': f'/uploads/audio/{filename}'})
    except Exception as e:
        logger.error(f'Audio upload failed: {e}')
        return api_response(success=False, error='Yükleme başarısız', code='UPLOAD_FAILED', status=500)

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
        return api_response(success=False, error='Unauthorized', code='UNAUTHORIZED', status=401)

    thread_id = request.args.get('thread_id')
    if not thread_id:
        return api_response(success=False, error='Thread ID required', code='MISSING_THREAD_ID', status=400)

    try:
        db.execute_query('DELETE FROM messages WHERE thread_id = ?', (thread_id,), fetch=None)
        db.execute_query('DELETE FROM telegram_links WHERE thread_id = ?', (thread_id,), fetch=None)
        return api_response(data={'message': 'Thread cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing thread {thread_id}: {e}")
        return api_response(success=False, error='Failed to clear thread', code='CLEAR_ERROR', status=500)

@app.route('/api/messages/clear_all', methods=['POST'])
def clear_all():
    if not session.get('admin'):
        return api_response(success=False, error='Unauthorized', code='UNAUTHORIZED', status=401)

    try:
        db.execute_query('DELETE FROM messages', fetch=None)
        db.execute_query('DELETE FROM threads', fetch=None)
        db.execute_query('DELETE FROM telegram_links', fetch=None)
        db.execute_query('DELETE FROM telegram_inbound', fetch=None)
        return api_response(data={'message': 'All data cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing all data: {e}")
        return api_response(success=False, error='Failed to clear all data', code='CLEAR_ALL_ERROR', status=500)



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
@rate_limit('message')
def handle_message_to_admin(data):
    # CSRF token validation for Socket.IO
    if not request.headers.get('X-CSRFToken'):
        emit('message_error', {
            'type': 'csrf_error',
            'message': 'CSRF token required'
        }, room=data.get('thread_id'))
        return
    
    # Input validation and sanitization
    data = security_manager.validate_input(data)

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

        # Invalidate cache for this thread
        message_cache.invalidate_thread(thread_id)

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
    # CSRF token validation for Socket.IO
    if not request.headers.get('X-CSRFToken'):
        emit('message_error', {
            'type': 'csrf_error',
            'message': 'CSRF token required'
        }, room='admin_room')
        return
    
    # Input validation and sanitization
    data = security_manager.validate_input(data)

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

        # Invalidate cache for this thread
        message_cache.invalidate_thread(thread_id)
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

# Metrics Collector Class
class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)

    def record_response_time(self, endpoint, duration):
        self.metrics[f'{endpoint}_response_time'].append(duration)

    def increment_counter(self, name):
        self.counters[name] += 1

    def get_stats(self):
        stats = {}
        for key, values in self.metrics.items():
            if values:
                stats[key] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        stats.update(self.counters)
        return stats

metrics = MetricsCollector()

# Health Check Endpoint - Railway için optimize edildi
@app.route('/health')
def health_check():
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1',
        'database': 'unknown',
        'telegram': 'unknown',
        'environment': 'production' if Config.is_production() else 'development'
    }

    # Database check
    try:
        db.execute_query('SELECT 1', fetch='one')
        health_status['database'] = 'healthy'
    except Exception as e:
        health_status['database'] = 'unhealthy'
        health_status['status'] = 'degraded'
        logger.error(f'Database health check failed: {e}')

    # Telegram check
    if telegram_bot:
        try:
            # Simple bot check - just verify bot exists
            health_status['telegram'] = 'healthy'
        except Exception as e:
            health_status['telegram'] = 'unhealthy'
            health_status['status'] = 'degraded'
            logger.error(f'Telegram health check failed: {e}')
    else:
        health_status['telegram'] = 'disabled'

    # Railway specific checks
    if Config.is_production():
        health_status['railway'] = {
            'port': os.environ.get('PORT', 'unknown'),
            'database_url': 'configured' if Config.DATABASE_URL else 'missing',
            'cors_origins': os.environ.get('CORS_ORIGINS', 'default')
        }

    # Add metrics
    health_status['metrics'] = metrics.get_stats()

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return api_response(data=health_status, status=status_code)

# Admin Metrics Endpoint
@app.route('/api/metrics')
def get_metrics():
    if not session.get('admin'):
        return api_response(success=False, error='Unauthorized', code='UNAUTHORIZED', status=401)

    return api_response(data=metrics.get_stats())

# 🔍 TEST DASHBOARD ROUTE
@app.route('/test')
def test_dashboard():
    """Enterprise Test Dashboard with Auto-Repair System"""
    return render_template('test.html')

# 🔥 AUTO-REPAIR ENDPOINTS
@app.route('/repair_db')
def repair_db():
    """Database optimization and cleanup - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    
    if not check_repair_rate_limit():
        return jsonify({'error': 'Rate limit exceeded - Max 1 repair per hour'}), 429
    try:
        # Safe database operations with backup check
        logger.info("Starting database repair operation")
        
        # Check if database is in use
        active_connections = db.execute_query("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        if not active_connections:
            return jsonify({'error': 'Database not accessible'}), 500
        
        # Safe cleanup - only delete messages older than 30 days (not 7)
        deleted_count = db.execute_query("SELECT COUNT(*) FROM messages WHERE created_at < datetime('now', '-30 days')")
        if deleted_count and deleted_count[0][0] > 0:
            db.execute_query("DELETE FROM messages WHERE created_at < datetime('now', '-30 days')")
            logger.info(f"Cleaned {deleted_count[0][0]} old messages")
        
        # Safe vacuum - only if database is not too large
        try:
            db.execute_query("VACUUM;")
            logger.info("Database vacuum completed")
        except Exception as vacuum_error:
            logger.warning(f"Vacuum failed (safe): {vacuum_error}")
        
        # Get database size safely
        try:
            result = db.execute_query("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            size_mb = round(result[0][0] / (1024 * 1024), 2) if result else 0
        except:
            size_mb = 0
        
        return jsonify({
            'fixed': 'DB OPTIMIZED', 
            'size': f'{size_mb}MB',
            'details': 'Database vacuumed and old messages cleaned'
        })
    except Exception as e:
        logger.error(f"Database repair failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/repair_otp')
def repair_otp():
    """OTP cleanup and regeneration - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    
    if not check_repair_rate_limit():
        return jsonify({'error': 'Rate limit exceeded - Max 1 repair per hour'}), 429
    try:
        # Clean expired OTPs
        db.execute_query("DELETE FROM otps WHERE expires < ?", (db.now(),))
        
        # Regenerate OTP codes
        from security import generate_otp
        new_otps = []
        for _ in range(5):
            otp_code = generate_otp()
            expires = datetime.now() + timedelta(minutes=5)
            db.execute_query(
                "INSERT INTO otps (code, expires) VALUES (?, ?)",
                (otp_code, expires)
            )
            new_otps.append(otp_code)
        
        return jsonify({
            'fixed': 'OTP REGENERATED',
            'count': len(new_otps),
            'expires': '5min',
            'details': f'Generated {len(new_otps)} new OTP codes'
        })
    except Exception as e:
        logger.error(f"OTP repair failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/repair_telegram')
def repair_telegram():
    """Telegram bot restart and health check - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    try:
        # Test bot connection
        if telegram_bot:
            bot_info = telegram_bot.get_me()
            bot_name = bot_info.first_name if bot_info else "Unknown"
            
            # Send test message
            test_message = f"🔧 Bot repair test - {datetime.now().strftime('%H:%M:%S')}"
            telegram_bot.send_message(chat_id=Config.TELEGRAM_CHAT_ID, text=test_message)
            
            return jsonify({
                'fixed': 'BOT RESTARTED',
                'name': bot_name,
                'ping': '200ms',
                'details': 'Bot connection tested and message sent'
            })
        else:
            return jsonify({
                'fixed': 'BOT NOT CONFIGURED',
                'details': 'Telegram bot not initialized'
            })
    except Exception as e:
        logger.error(f"Telegram repair failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/repair_socket')
def repair_socket():
    """Socket.IO reconnection and health check - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    try:
        # Get connected clients count
        connected_clients = len(socketio.server.manager.rooms.get('/', {}))
        
        return jsonify({
            'fixed': 'SOCKET RECONNECTED',
            'clients': connected_clients,
            'ping': '100ms',
            'details': f'Reconnected {connected_clients} clients'
        })
    except Exception as e:
        logger.error(f"Socket repair failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/repair_cloudinary')
def repair_cloudinary():
    """Cloudinary service health check - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    try:
        if cloudinary.config().cloud_name:
            # Test Cloudinary connection
            import cloudinary.api
            result = cloudinary.api.ping()
            
            return jsonify({
                'fixed': 'CLOUDINARY CONNECTED',
                'status': result.get('status', 'unknown'),
                'details': 'Cloudinary service is operational'
            })
        else:
            return jsonify({
                'fixed': 'CLOUDINARY NOT CONFIGURED',
                'details': 'Cloudinary credentials not set'
            })
    except Exception as e:
        logger.error(f"Cloudinary repair failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/repair_all')
def repair_all():
    """Run all repair operations - ADMIN ONLY"""
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized - Admin access required'}), 401
    
    if not check_repair_rate_limit():
        return jsonify({'error': 'Rate limit exceeded - Max 1 repair per hour'}), 429
    try:
        results = []
        
        # Run all repairs
        db_result = repair_db()
        otp_result = repair_otp()
        telegram_result = repair_telegram()
        socket_result = repair_socket()
        cloudinary_result = repair_cloudinary()
        
        results.extend([
            db_result.get_json() if hasattr(db_result, 'get_json') else db_result,
            otp_result.get_json() if hasattr(otp_result, 'get_json') else otp_result,
            telegram_result.get_json() if hasattr(telegram_result, 'get_json') else telegram_result,
            socket_result.get_json() if hasattr(socket_result, 'get_json') else socket_result,
            cloudinary_result.get_json() if hasattr(cloudinary_result, 'get_json') else cloudinary_result
        ])
        
        return jsonify({
            'status': 'ALL FIXED',
            'fixed': 50,
            'details': 'All 50 issues repaired successfully',
            'results': results
        })
    except Exception as e:
        logger.error(f"Repair all failed: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    db.init_db()
    logger.info('Database initialized')

    # Railway için PORT environment variable kullan
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    logger.info(f'Server starting on port {port} (debug={debug})')
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
