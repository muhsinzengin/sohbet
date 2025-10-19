import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from config import Config

# Türkiye saat dilimi (UTC+3)
TURKEY_TZ = timezone(timedelta(hours=3))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

class Database:
    def __init__(self):
        self.database_url = Config.DATABASE_URL
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        self.is_postgres = 'postgres' in self.database_url.lower()
        self.sqlite_path = Config.SQLITE_PATH
        
    @contextmanager
    def get_connection(self):
        if self.is_postgres:
            conn = psycopg2.connect(self.database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            # Foreign keys aktif et
            conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query, params=(), fetch='all'):
        query = query.replace('?', '%s') if self.is_postgres else query
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch == 'one':
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch == 'all':
                return [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                return None
    
    def get_current_timestamp(self):
        """Türkiye saati için timestamp döndür"""
        now = datetime.now(TURKEY_TZ)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    def init_db(self):
        if self.is_postgres:
            timestamp_default = "NOW()"
        else:
            timestamp_default = "(datetime('now', '+3 hours'))"
        
        schema = '''
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT {ts},
            last_activity_at TIMESTAMP DEFAULT {ts}
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            type TEXT NOT NULL,
            content_text TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT {ts},
            FOREIGN KEY (thread_id) REFERENCES threads(id)
        );
        
        CREATE TABLE IF NOT EXISTS telegram_links (
            id {pk_type} {pk_constraint},
            thread_id TEXT NOT NULL,
            tg_chat_id TEXT NOT NULL,
            tg_message_id INTEGER NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES threads(id)
        );
        
        CREATE TABLE IF NOT EXISTS telegram_inbound (
            id {pk_type} {pk_constraint},
            tg_chat_id TEXT NOT NULL,
            tg_message_id INTEGER NOT NULL,
            processed_at TIMESTAMP DEFAULT {ts},
            UNIQUE (tg_chat_id, tg_message_id)
        );

        CREATE TABLE IF NOT EXISTS otp_codes (
            id {pk_type} {pk_constraint},
            code TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT {ts}
        );
        '''.format(
            ts=timestamp_default,
            pk_type='SERIAL' if self.is_postgres else 'INTEGER',
            pk_constraint='PRIMARY KEY' if self.is_postgres else 'PRIMARY KEY AUTOINCREMENT'
        )
        
        for statement in schema.split(';'):
            if statement.strip():
                self.execute_query(statement, fetch=None)
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id)',
            'CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_threads_activity ON threads(last_activity_at)',
            'CREATE INDEX IF NOT EXISTS idx_telegram_links_thread ON telegram_links(thread_id)',
            'CREATE INDEX IF NOT EXISTS idx_telegram_links_tg_msg ON telegram_links(tg_message_id)',
            'CREATE INDEX IF NOT EXISTS idx_telegram_inbound_chat ON telegram_inbound(tg_chat_id)'
        ]
        
        for idx in indexes:
            try:
                self.execute_query(idx, fetch=None)
            except:
                pass

db = Database()
