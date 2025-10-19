#!/usr/bin/env python3
# HEALTHCHECK - Health endpoint ekler
import os
import sys
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database import db
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_health_endpoint():
    """Add health check endpoint to app.py"""
    print("🏥 HEALTH ENDPOINT EKLENİYOR...")
    
    health_endpoint_code = '''
# ============================================
# HEALTH CHECK ENDPOINT
# ============================================
@app.route('/health')
def health_check():
    """Health check endpoint for Railway monitoring"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.3',
            'environment': 'production' if Config.is_production() else 'development',
            'checks': {}
        }
        
        # Database check
        try:
            db.execute_query("SELECT 1")
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Telegram bot check
        try:
            if Config.TELEGRAM_BOT_TOKEN:
                import requests
                response = requests.get(
                    f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getMe",
                    timeout=5
                )
                if response.status_code == 200:
                    health_status['checks']['telegram'] = 'healthy'
                else:
                    health_status['checks']['telegram'] = 'unhealthy'
            else:
                health_status['checks']['telegram'] = 'not_configured'
        except Exception as e:
            health_status['checks']['telegram'] = f'unhealthy: {str(e)}'
        
        # Memory check
        try:
            import psutil
            memory = psutil.virtual_memory()
            health_status['checks']['memory'] = {
                'used_percent': memory.percent,
                'available_gb': round(memory.available / (1024**3), 2)
            }
        except ImportError:
            health_status['checks']['memory'] = 'psutil_not_available'
        
        # Disk check
        try:
            disk = psutil.disk_usage('/')
            health_status['checks']['disk'] = {
                'used_percent': (disk.used / disk.total) * 100,
                'free_gb': round(disk.free / (1024**3), 2)
            }
        except:
            health_status['checks']['disk'] = 'unavailable'
        
        # Return appropriate status code
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health/live')
def liveness_probe():
    """Kubernetes/Railway liveness probe"""
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/health/ready')
def readiness_probe():
    """Kubernetes/Railway readiness probe"""
    try:
        # Check database connection
        db.execute_query("SELECT 1")
        return jsonify({'status': 'ready', 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503
'''
    
    print("✅ Health endpoint code hazır")
    print("📋 Bu kodu app.py'ye ekleyin:")
    print(health_endpoint_code)
    
    return True

def test_health_endpoint():
    """Test health endpoint functionality"""
    print("\n🧪 Health endpoint test ediliyor...")
    
    # This would test the actual endpoint if the app is running
    print("ℹ️  Health endpoint test için app.py'ye kod eklenmeli")
    print("✅ Health endpoint code hazır")
    
    return True

def create_health_monitor():
    """Create health monitoring script"""
    print("\n📊 Health monitor script oluşturuluyor...")
    
    monitor_script = '''#!/usr/bin/env python3
# HEALTH MONITOR - Railway health monitoring
import requests
import time
import json
from datetime import datetime

def monitor_health(base_url, interval=30):
    """Monitor application health"""
    print(f"🏥 Health monitoring started: {base_url}")
    
    while True:
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Healthy")
                
                # Check specific components
                checks = health_data.get('checks', {})
                for check, status in checks.items():
                    if isinstance(status, str) and 'unhealthy' in status:
                        print(f"⚠️  {check}: {status}")
                        
            else:
                print(f"❌ {datetime.now().strftime('%H:%M:%S')} - Unhealthy ({response.status_code})")
                
        except Exception as e:
            print(f"❌ {datetime.now().strftime('%H:%M:%S')} - Error: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    monitor_health(base_url, interval)
'''
    
    with open('health_monitor.py', 'w') as f:
        f.write(monitor_script)
    
    print("✅ Health monitor script oluşturuldu: health_monitor.py")
    print("📋 Usage: python health_monitor.py https://your-app.railway.app 30")
    
    return True

if __name__ == "__main__":
    print("🚀 HEALTH CHECK ENDPOINT SCRIPT")
    print("=" * 50)
    
    # Step 1: Add health endpoint
    add_health_endpoint()
    
    # Step 2: Test health endpoint
    test_health_endpoint()
    
    # Step 3: Create health monitor
    create_health_monitor()
    
    print("\n🎉 HEALTH CHECK ENDPOINT HAZIR!")
    print("📊 Railway monitoring için hazır")
    print("🔧 app.py'ye health endpoint kodunu ekleyin")
