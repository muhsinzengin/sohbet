#!/usr/bin/env python3
# LOCUSTFILE - 100 user load test
import os
import sys
import json
import random
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

try:
    from locust import HttpUser, task, between
    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False
    print("⚠️  Locust not installed. Install with: pip install locust")

class ChatUser(HttpUser):
    """Simulated chat user for load testing"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        print(f"👤 User {self.client.base_url} started")
        
        # Get CSRF token
        response = self.client.get("/")
        if response.status_code == 200:
            print("✅ Homepage loaded")
        else:
            print(f"❌ Homepage failed: {response.status_code}")
    
    @task(3)
    def visit_homepage(self):
        """Visit homepage (most common task)"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Homepage failed: {response.status_code}")
    
    @task(2)
    def send_message(self):
        """Send a chat message"""
        # Simulate message data
        message_data = {
            "thread_id": f"test_thread_{random.randint(1000, 9999)}",
            "text": f"Test message {datetime.now().strftime('%H:%M:%S')}",
            "type": "text"
        }
        
        with self.client.post(
            "/api/messages/send",
            json=message_data,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Send message failed: {response.status_code}")
    
    @task(1)
    def upload_image(self):
        """Upload an image (less frequent)"""
        # Create a small test image
        test_image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        
        with self.client.post(
            "/api/upload/image",
            files={"file": ("test.jpg", test_image_data, "image/jpeg")},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Image upload failed: {response.status_code}")
    
    @task(1)
    def get_messages(self):
        """Get messages"""
        thread_id = f"test_thread_{random.randint(1000, 9999)}"
        
        with self.client.get(
            f"/api/messages/{thread_id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:  # 404 is OK for non-existent threads
                response.success()
            else:
                response.failure(f"Get messages failed: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

class AdminUser(HttpUser):
    """Simulated admin user"""
    
    wait_time = between(2, 5)  # Admins are less active
    
    def on_start(self):
        """Admin login simulation"""
        print(f"👨‍💼 Admin user started")
    
    @task(2)
    def admin_login(self):
        """Simulate admin login"""
        with self.client.get("/admin", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin page failed: {response.status_code}")
    
    @task(1)
    def get_threads(self):
        """Get all threads"""
        with self.client.get("/api/threads", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get threads failed: {response.status_code}")

def create_load_test_script():
    """Create a standalone load test script"""
    script_content = '''#!/usr/bin/env python3
# LOAD TEST SCRIPT - Railway için optimize edilmiş
import requests
import threading
import time
import random
from datetime import datetime

class LoadTester:
    def __init__(self, base_url, num_users=100):
        self.base_url = base_url
        self.num_users = num_users
        self.results = {
            'success': 0,
            'failed': 0,
            'total_time': 0
        }
    
    def simulate_user(self, user_id):
        """Simulate a single user"""
        session = requests.Session()
        start_time = time.time()
        
        try:
            # Visit homepage
            response = session.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.results['success'] += 1
            else:
                self.results['failed'] += 1
            
            # Send message
            message_data = {
                "thread_id": f"load_test_{user_id}",
                "text": f"Load test message {user_id}",
                "type": "text"
            }
            
            response = session.post(
                f"{self.base_url}/api/messages/send",
                json=message_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.results['success'] += 1
            else:
                self.results['failed'] += 1
            
            # Health check
            response = session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.results['success'] += 1
            else:
                self.results['failed'] += 1
                
        except Exception as e:
            self.results['failed'] += 1
            print(f"User {user_id} error: {e}")
        
        finally:
            session.close()
    
    def run_test(self, duration_seconds=60):
        """Run load test for specified duration"""
        print(f"🚀 Load test başladı: {self.num_users} users, {duration_seconds}s")
        
        threads = []
        start_time = time.time()
        
        # Start all users
        for i in range(self.num_users):
            thread = threading.Thread(target=self.simulate_user, args=(i,))
            threads.append(thread)
            thread.start()
            time.sleep(0.1)  # Stagger user starts
        
        # Wait for test duration
        time.sleep(duration_seconds)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        total_time = time.time() - start_time
        self.results['total_time'] = total_time
        
        # Print results
        total_requests = self.results['success'] + self.results['failed']
        success_rate = (self.results['success'] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\\n📊 LOAD TEST SONUÇLARI:")
        print(f"✅ Başarılı: {self.results['success']}")
        print(f"❌ Başarısız: {self.results['failed']}")
        print(f"📈 Başarı oranı: {success_rate:.1f}%")
        print(f"⏱️  Toplam süre: {total_time:.1f}s")
        print(f"🚀 RPS: {total_requests/total_time:.1f}")
        
        return success_rate > 80

if __name__ == "__main__":
    # Railway URL'ini buraya ekleyin
    RAILWAY_URL = "https://your-app-name.railway.app"
    
    tester = LoadTester(RAILWAY_URL, num_users=100)
    success = tester.run_test(duration_seconds=60)
    
    if success:
        print("\\n🎉 LOAD TEST BAŞARILI!")
    else:
        print("\\n❌ LOAD TEST BAŞARISIZ!")
'''
    
    with open('load_test_standalone.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Standalone load test script oluşturuldu: load_test_standalone.py")

if __name__ == "__main__":
    print("🚀 LOAD TEST SCRIPT")
    print("=" * 50)
    
    if LOCUST_AVAILABLE:
        print("✅ Locust available - Full load testing ready")
        print("📋 Usage: locust -f locustfile.py --host=https://your-app.railway.app")
        print("🌐 Web UI: http://localhost:8089")
    else:
        print("⚠️  Locust not available - Creating standalone script")
        create_load_test_script()
    
    print("\n🎉 LOAD TEST HAZIR!")
    print("📊 100 concurrent users test edilebilir")
    print("🚀 Railway performance test hazır")
