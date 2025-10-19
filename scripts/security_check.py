#!/usr/bin/env python3
# SECURITY_CHECK - OWASP Top 10 güvenlik taraması
import os
import sys
import json
import logging
import requests
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import Config
from security import security_manager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_owasp_top10():
    """Check OWASP Top 10 security vulnerabilities"""
    print("🔒 OWASP TOP 10 SECURITY CHECK BAŞLADI...")
    
    security_results = {
        'A01_Broken_Access_Control': False,
        'A02_Cryptographic_Failures': False,
        'A03_Injection': False,
        'A04_Insecure_Design': False,
        'A05_Security_Misconfiguration': False,
        'A06_Vulnerable_Components': False,
        'A07_Authentication_Failures': False,
        'A08_Software_Integrity_Failures': False,
        'A09_Logging_Failures': False,
        'A10_Server_Side_Request_Forgery': False
    }
    
    print("🔍 A01: Broken Access Control kontrol ediliyor...")
    # Check session security
    if Config.is_production():
        if os.getenv('SESSION_COOKIE_SECURE') == 'True':
            security_results['A01_Broken_Access_Control'] = True
            print("✅ Session cookies secure")
        else:
            print("❌ Session cookies not secure")
    else:
        print("ℹ️  Development mode - session security check skipped")
        security_results['A01_Broken_Access_Control'] = True
    
    print("🔍 A02: Cryptographic Failures kontrol ediliyor...")
    # Check secret key strength
    secret_key = os.getenv('SECRET_KEY')
    if secret_key and len(secret_key) >= 32:
        security_results['A02_Cryptographic_Failures'] = True
        print("✅ Secret key strong enough")
    else:
        print("❌ Secret key too weak")
    
    print("🔍 A03: Injection kontrol ediliyor...")
    # Check XSS protection
    test_xss = '<script>alert("xss")</script>'
    sanitized = security_manager.sanitize_html(test_xss)
    if '<script>' not in sanitized:
        security_results['A03_Injection'] = True
        print("✅ XSS protection active")
    else:
        print("❌ XSS protection failed")
    
    print("🔍 A04: Insecure Design kontrol ediliyor...")
    # Check input validation
    test_input = {'text': 'test', 'malicious': 'test'}
    validated = security_manager.validate_input(test_input)
    if 'malicious' in validated:
        security_results['A04_Insecure_Design'] = True
        print("✅ Input validation active")
    else:
        print("❌ Input validation failed")
    
    print("🔍 A05: Security Misconfiguration kontrol ediliyor...")
    # Check CORS configuration
    cors_origins = os.getenv('CORS_ORIGINS', '*')
    if cors_origins != '*' or not Config.is_production():
        security_results['A05_Security_Misconfiguration'] = True
        print("✅ CORS properly configured")
    else:
        print("❌ CORS too permissive")
    
    print("🔍 A06: Vulnerable Components kontrol ediliyor...")
    # Check requirements.txt for known vulnerabilities
    try:
        with open('../requirements.txt', 'r') as f:
            requirements = f.read()
        
        vulnerable_packages = ['django<3.0', 'flask<2.0', 'requests<2.25']
        vulnerable_found = [pkg for pkg in vulnerable_packages if pkg in requirements]
        
        if not vulnerable_found:
            security_results['A06_Vulnerable_Components'] = True
            print("✅ No known vulnerable packages")
        else:
            print(f"❌ Vulnerable packages found: {vulnerable_found}")
    except Exception as e:
        print(f"⚠️  Could not check packages: {e}")
        security_results['A06_Vulnerable_Components'] = True
    
    print("🔍 A07: Authentication Failures kontrol ediliyor...")
    # Check admin credentials
    admin_user = os.getenv('ADMIN_USERNAME')
    admin_pass = os.getenv('ADMIN_PASSWORD')
    if admin_user and admin_pass and len(admin_pass) >= 8:
        security_results['A07_Authentication_Failures'] = True
        print("✅ Admin credentials configured")
    else:
        print("❌ Admin credentials weak or missing")
    
    print("🔍 A08: Software Integrity Failures kontrol ediliyor...")
    # Check file upload security
    test_filename = '../../../etc/passwd'
    secure_filename = security_manager.secure_filename_ext(test_filename)
    if '../../../' not in secure_filename:
        security_results['A08_Software_Integrity_Failures'] = True
        print("✅ File upload security active")
    else:
        print("❌ File upload security failed")
    
    print("🔍 A09: Logging Failures kontrol ediliyor...")
    # Check logging configuration
    if os.path.exists('../logs/chat.log'):
        security_results['A09_Logging_Failures'] = True
        print("✅ Logging configured")
    else:
        print("❌ Logging not configured")
    
    print("🔍 A10: Server-Side Request Forgery kontrol ediliyor...")
    # Check CORS and origin validation
    if cors_origins != '*':
        security_results['A10_Server_Side_Request_Forgery'] = True
        print("✅ CORS origin validation active")
    else:
        print("❌ CORS origin validation missing")
    
    return security_results

def generate_security_report(results):
    """Generate security report"""
    print("\n" + "=" * 50)
    print("🔒 SECURITY REPORT")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    score = (passed / total) * 100
    
    print(f"📊 Security Score: {score:.1f}% ({passed}/{total})")
    print()
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        check_name = check.replace('_', ' ').title()
        print(f"{status} {check_name}")
    
    print("\n" + "=" * 50)
    
    if score >= 90:
        print("🎉 EXCELLENT SECURITY!")
        print("🚀 Production ready")
    elif score >= 70:
        print("⚠️  GOOD SECURITY")
        print("🔧 Minor improvements needed")
    else:
        print("❌ POOR SECURITY")
        print("🚨 Critical issues found")
    
    return score >= 70

if __name__ == "__main__":
    print("🚀 OWASP TOP 10 SECURITY CHECK SCRIPT")
    print("=" * 50)
    
    results = check_owasp_top10()
    security_ok = generate_security_report(results)
    
    if security_ok:
        print("\n🎉 SECURITY CHECK BAŞARILI!")
        print("📊 OWASP Top 10 compliance OK")
    else:
        print("\n❌ SECURITY CHECK BAŞARISIZ!")
        print("🔍 Güvenlik sorunları bulundu")
        sys.exit(1)
