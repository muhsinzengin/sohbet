import sqlite3
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

class MessageSearch:
    def __init__(self, db_path='chat.db'):
        self.db_path = db_path

    def search_messages(self, query: str, thread_id=None, sender=None, limit=50, offset=0) -> List[Dict[str, Any]]:
        """Mesajlarda arama yap"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Arama sorgusu oluştur
            sql = """
                SELECT m.*, t.display_name as thread_name
                FROM messages m
                LEFT JOIN threads t ON m.thread_id = t.id
                WHERE 1=1
            """
            params = []

            # Metin arama (şifrelenmiş mesajlar için basit arama)
            if query:
                # Basit kelime arama (şifrelenmiş olduğu için sınırlı)
                search_terms = query.lower().split()
                text_conditions = []
                for term in search_terms:
                    text_conditions.append("LOWER(m.content_text) LIKE ?")
                    params.append(f"%{term}%")
                if text_conditions:
                    sql += " AND (" + " OR ".join(text_conditions) + ")"

            # Thread filtresi
            if thread_id:
                sql += " AND m.thread_id = ?"
                params.append(thread_id)

            # Gönderen filtresi
            if sender:
                sql += " AND m.sender = ?"
                params.append(sender)

            # Sıralama ve limit
            sql += " ORDER BY m.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Şifrelenmiş mesajları decrypt et (eğer mümkünse)
            for msg in results:
                if msg['content_text'] and msg['type'] == 'text':
                    try:
                        # Burada ENCRYPTION_KEY'e erişim gerekli
                        # Şimdilik şifrelenmiş olarak bırak
                        pass
                    except:
                        pass

            conn.close()
            return results

        except Exception as e:
            print(f"Arama hatası: {e}")
            return []

    def search_by_date_range(self, start_date: str, end_date: str, thread_id=None) -> List[Dict[str, Any]]:
        """Tarih aralığında arama"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = """
                SELECT m.*, t.display_name as thread_name
                FROM messages m
                LEFT JOIN threads t ON m.thread_id = t.id
                WHERE DATE(m.created_at) BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if thread_id:
                sql += " AND m.thread_id = ?"
                params.append(thread_id)

            sql += " ORDER BY m.created_at DESC"

            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results

        except Exception as e:
            print(f"Tarih arama hatası: {e}")
            return []

    def get_message_stats(self, thread_id=None) -> Dict[str, Any]:
        """Mesaj istatistikleri"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Toplam mesaj sayısı
            if thread_id:
                cursor.execute("SELECT COUNT(*) FROM messages WHERE thread_id = ?", (thread_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]

            # Gönderen bazlı istatistikler
            if thread_id:
                cursor.execute("""
                    SELECT sender, COUNT(*) as count
                    FROM messages
                    WHERE thread_id = ?
                    GROUP BY sender
                    ORDER BY count DESC
                """, (thread_id,))
            else:
                cursor.execute("""
                    SELECT sender, COUNT(*) as count
                    FROM messages
                    GROUP BY sender
                    ORDER BY count DESC
                """)

            sender_stats = cursor.fetchall()

            # Günlük mesaj sayısı (son 30 gün)
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM messages
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            daily_stats = cursor.fetchall()

            # Mesaj tipi istatistikleri
            if thread_id:
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM messages
                    WHERE thread_id = ?
                    GROUP BY type
                    ORDER BY count DESC
                """, (thread_id,))
            else:
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM messages
                    GROUP BY type
                    ORDER BY count DESC
                """)

            type_stats = cursor.fetchall()

            conn.close()

            return {
                'total_messages': total_messages,
                'sender_stats': [{'sender': s[0], 'count': s[1]} for s in sender_stats],
                'daily_stats': [{'date': d[0], 'count': d[1]} for d in daily_stats],
                'type_stats': [{'type': t[0], 'count': t[1]} for t in type_stats]
            }

        except Exception as e:
            print(f"İstatistik hatası: {e}")
            return {}

    def get_recent_messages(self, limit=10, thread_id=None) -> List[Dict[str, Any]]:
        """Son mesajları getir"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if thread_id:
                cursor.execute("""
                    SELECT m.*, t.display_name as thread_name
                    FROM messages m
                    LEFT JOIN threads t ON m.thread_id = t.id
                    WHERE m.thread_id = ?
                    ORDER BY m.created_at DESC
                    LIMIT ?
                """, (thread_id, limit))
            else:
                cursor.execute("""
                    SELECT m.*, t.display_name as thread_name
                    FROM messages m
                    LEFT JOIN threads t ON m.thread_id = t.id
                    ORDER BY m.created_at DESC
                    LIMIT ?
                """, (limit,))

            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results

        except Exception as e:
            print(f"Son mesajlar hatası: {e}")
            return []

# Flask route'ları için yardımcı fonksiyonlar
def add_search_routes(app):
    """Flask app'e arama route'larını ekle"""

    search_engine = MessageSearch()

    @app.route('/api/search/messages', methods=['GET'])
    def search_messages_api():
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        query = request.args.get('q', '')
        thread_id = request.args.get('thread_id')
        sender = request.args.get('sender')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        results = search_engine.search_messages(query, thread_id, sender, limit, offset)
        return jsonify(results)

    @app.route('/api/search/stats', methods=['GET'])
    def get_message_stats_api():
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        thread_id = request.args.get('thread_id')
        stats = search_engine.get_message_stats(thread_id)
        return jsonify(stats)

    @app.route('/api/search/recent', methods=['GET'])
    def get_recent_messages_api():
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        limit = int(request.args.get('limit', 10))
        thread_id = request.args.get('thread_id')
        messages = search_engine.get_recent_messages(limit, thread_id)
        return jsonify(messages)

    @app.route('/api/search/date_range', methods=['GET'])
    def search_by_date_api():
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        start_date = request.args.get('start')
        end_date = request.args.get('end')
        thread_id = request.args.get('thread_id')

        if not start_date or not end_date:
            return jsonify({'error': 'start ve end tarihleri gerekli'}), 400

        results = search_engine.search_by_date_range(start_date, end_date, thread_id)
        return jsonify(results)

if __name__ == '__main__':
    # Test
    search = MessageSearch()
    print("Son 5 mesaj:")
    recent = search.get_recent_messages(5)
    for msg in recent:
        print(f"  {msg['sender']}: {msg['content_text'][:50]}...")

    print("\nİstatistikler:")
    stats = search.get_message_stats()
    print(f"Toplam mesaj: {stats.get('total_messages', 0)}")
