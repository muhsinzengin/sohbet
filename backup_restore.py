import os
import json
import sqlite3
import zipfile
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class BackupManager:
    def __init__(self, db_path='chat.db', backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.encryption_key = self._generate_key()

        # Backup klasörünü oluştur
        os.makedirs(backup_dir, exist_ok=True)

    def _generate_key(self):
        """Backup şifreleme anahtarı üret"""
        password = os.getenv('BACKUP_ENCRYPTION_KEY', 'default_backup_key_change_in_production')
        salt = b'backup_salt_2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def create_backup(self, include_files=True):
        """Tam backup oluştur"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"chat_backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Database backup
                if os.path.exists(self.db_path):
                    zipf.write(self.db_path, 'database/chat.db')

                # Upload files backup
                if include_files and os.path.exists('uploads'):
                    for root, dirs, files in os.walk('uploads'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('uploads', os.path.relpath(file_path, 'uploads'))
                            zipf.write(file_path, arcname)

                # Config backup (şifrelenmiş)
                config_data = {
                    'timestamp': timestamp,
                    'version': '1.0',
                    'db_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                }
                config_json = json.dumps(config_data).encode()
                encrypted_config = Fernet(self.encryption_key).encrypt(config_json)
                zipf.writestr('backup_info.enc', encrypted_config)

            # Backup boyutunu logla
            backup_size = os.path.getsize(backup_path)
            print(f"✅ Backup oluşturuldu: {backup_path} ({backup_size / 1024 / 1024:.1f} MB)")

            return backup_path

        except Exception as e:
            print(f"❌ Backup oluşturma hatası: {e}")
            return None

    def restore_backup(self, backup_path, restore_files=True):
        """Backup'tan geri yükle"""
        if not os.path.exists(backup_path):
            print(f"❌ Backup dosyası bulunamadı: {backup_path}")
            return False

        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Geçici klasör oluştur
                temp_dir = f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(temp_dir, exist_ok=True)

                try:
                    # Dosyaları çıkar
                    zipf.extractall(temp_dir)

                    # Database geri yükle
                    db_backup = os.path.join(temp_dir, 'database', 'chat.db')
                    if os.path.exists(db_backup):
                        # Mevcut database'i yedekle
                        if os.path.exists(self.db_path):
                            backup_db = f"{self.db_path}.backup"
                            os.rename(self.db_path, backup_db)
                            print(f"📋 Eski database yedeklendi: {backup_db}")

                        # Yeni database'i kopyala
                        os.rename(db_backup, self.db_path)
                        print("✅ Database geri yüklendi")

                    # Upload files geri yükle
                    if restore_files:
                        uploads_backup = os.path.join(temp_dir, 'uploads')
                        if os.path.exists(uploads_backup):
                            import shutil
                            if os.path.exists('uploads'):
                                shutil.move('uploads', 'uploads.backup')
                            shutil.move(uploads_backup, 'uploads')
                            print("✅ Upload dosyaları geri yüklendi")

                    # Backup info kontrolü
                    if 'backup_info.enc' in zipf.namelist():
                        with zipf.open('backup_info.enc') as f:
                            encrypted_data = f.read()
                            decrypted_data = Fernet(self.encryption_key).decrypt(encrypted_data)
                            info = json.loads(decrypted_data.decode())
                            print(f"📋 Backup bilgisi: {info}")

                    print("✅ Geri yükleme tamamlandı")
                    return True

                finally:
                    # Temizlik
                    import shutil
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)

        except Exception as e:
            print(f"❌ Geri yükleme hatası: {e}")
            return False

    def list_backups(self):
        """Mevcut backup'ları listele"""
        if not os.path.exists(self.backup_dir):
            return []

        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith('.zip'):
                path = os.path.join(self.backup_dir, file)
                size = os.path.getsize(path)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                backups.append({
                    'name': file,
                    'path': path,
                    'size_mb': size / 1024 / 1024,
                    'created': mtime.strftime('%Y-%m-%d %H:%M:%S')
                })

        return sorted(backups, key=lambda x: x['created'], reverse=True)

    def cleanup_old_backups(self, keep_days=30):
        """Eski backup'ları temizle"""
        import time

        if not os.path.exists(self.backup_dir):
            return

        now = time.time()
        deleted = 0

        for file in os.listdir(self.backup_dir):
            if file.endswith('.zip'):
                path = os.path.join(self.backup_dir, file)
                if now - os.path.getmtime(path) > keep_days * 24 * 3600:
                    os.remove(path)
                    deleted += 1
                    print(f"🗑️ Eski backup silindi: {file}")

        if deleted > 0:
            print(f"✅ {deleted} eski backup temizlendi")
        else:
            print("ℹ️ Temizlenecek eski backup bulunamadı")

# CLI interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  python backup_restore.py create          # Yeni backup oluştur")
        print("  python backup_restore.py list            # Backup'ları listele")
        print("  python backup_restore.py restore <file>  # Backup'tan geri yükle")
        print("  python backup_restore.py cleanup         # Eski backup'ları temizle")
        sys.exit(1)

    manager = BackupManager()

    command = sys.argv[1]

    if command == 'create':
        path = manager.create_backup()
        if path:
            print(f"Backup oluşturuldu: {path}")

    elif command == 'list':
        backups = manager.list_backups()
        if backups:
            print("Mevcut Backup'lar:")
            for b in backups:
                print(f"  {b['name']} - {b['size_mb']:.1f} MB - {b['created']}")
        else:
            print("Hiç backup bulunamadı")

    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Hata: Backup dosyası belirtin")
            sys.exit(1)

        backup_file = sys.argv[2]
        success = manager.restore_backup(backup_file)
        if success:
            print("Geri yükleme başarılı")
        else:
            print("Geri yükleme başarısız")

    elif command == 'cleanup':
        manager.cleanup_old_backups()
    else:
        print(f"Bilinmeyen komut: {command}")
