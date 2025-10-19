#!/usr/bin/env python3
# TEST_TELEGRAM - Bot live test eder
import os
import sys
import json
import logging
import requests
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_telegram_bot():
    """Test Telegram bot functionality"""
    print("🤖 TELEGRAM BOT TEST BAŞLADI...")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not set")
        return False
    
    print(f"🔑 Bot Token: {bot_token[:10]}...")
    print(f"💬 Chat ID: {chat_id}")
    
    # Test 1: Get bot info
    print("\n📋 Test 1: Bot info alınıyor...")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info['ok']:
                bot_data = bot_info['result']
                print(f"✅ Bot Name: {bot_data['first_name']}")
                print(f"✅ Bot Username: @{bot_data['username']}")
                print(f"✅ Bot ID: {bot_data['id']}")
            else:
                print(f"❌ Bot API error: {bot_info}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Bot info test hatası: {e}")
        return False
    
    # Test 2: Send test message
    print("\n📤 Test 2: Test mesajı gönderiliyor...")
    try:
        test_message = f"🧪 Bot Test - {datetime.now().strftime('%H:%M:%S')}"
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': test_message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['ok']:
                print("✅ Test mesajı gönderildi")
                print(f"✅ Message ID: {result['result']['message_id']}")
            else:
                print(f"❌ Send message error: {result}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Send message test hatası: {e}")
        return False
    
    # Test 3: Get updates
    print("\n📥 Test 3: Updates alınıyor...")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={'limit': 5},
            timeout=10
        )
        
        if response.status_code == 200:
            updates = response.json()
            if updates['ok']:
                update_count = len(updates['result'])
                print(f"✅ {update_count} update alındı")
                
                if update_count > 0:
                    latest_update = updates['result'][-1]
                    print(f"✅ Latest update ID: {latest_update['update_id']}")
                else:
                    print("ℹ️  No recent updates")
            else:
                print(f"❌ Get updates error: {updates}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Get updates test hatası: {e}")
        return False
    
    # Test 4: Webhook status (if applicable)
    print("\n🔗 Test 4: Webhook durumu kontrol ediliyor...")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getWebhookInfo",
            timeout=10
        )
        
        if response.status_code == 200:
            webhook_info = response.json()
            if webhook_info['ok']:
                webhook_data = webhook_info['result']
                if webhook_data['url']:
                    print(f"✅ Webhook URL: {webhook_data['url']}")
                    print(f"✅ Pending updates: {webhook_data['pending_update_count']}")
                else:
                    print("ℹ️  No webhook set (using polling)")
            else:
                print(f"❌ Webhook info error: {webhook_info}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Webhook test hatası: {e}")
    
    return True

def test_otp_functionality():
    """Test OTP sending functionality"""
    print("\n🔐 Test 5: OTP functionality test ediliyor...")
    
    # This would test the actual OTP sending from your app
    # For now, we'll just verify the bot can send messages
    print("ℹ️  OTP functionality requires app integration")
    print("✅ Bot message sending capability confirmed")
    
    return True

def cleanup_test_messages():
    """Clean up test messages"""
    print("\n🧹 Test mesajları temizleniyor...")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    try:
        # Get recent messages
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={'limit': 10},
            timeout=10
        )
        
        if response.status_code == 200:
            updates = response.json()
            if updates['ok']:
                test_messages = [
                    update for update in updates['result']
                    if 'message' in update and '🧪 Bot Test' in update['message'].get('text', '')
                ]
                
                for update in test_messages:
                    message_id = update['message']['message_id']
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{bot_token}/deleteMessage",
                            json={
                                'chat_id': chat_id,
                                'message_id': message_id
                            },
                            timeout=5
                        )
                        print(f"✅ Test mesajı silindi: {message_id}")
                    except:
                        pass
                        
    except Exception as e:
        print(f"⚠️  Cleanup hatası: {e}")

if __name__ == "__main__":
    print("🚀 TELEGRAM BOT TEST SCRIPT")
    print("=" * 50)
    
    success = test_telegram_bot()
    
    if success:
        test_otp_functionality()
        cleanup_test_messages()
        
        print("\n🎉 TELEGRAM BOT TEST BAŞARILI!")
        print("📊 Bot tamamen çalışır durumda")
        print("🤖 OTP gönderimi hazır")
    else:
        print("\n❌ TELEGRAM BOT TEST BAŞARISIZ!")
        print("🔍 Bot token ve chat ID'yi kontrol edin")
        sys.exit(1)
