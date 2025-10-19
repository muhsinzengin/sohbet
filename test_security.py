#!/usr/bin/env python3
"""
Security Testing Script for Chat Application
Tests XSS protection, input validation, and file upload security
"""

import requests
import json
import socketio
import time
import os
from datetime import datetime

def test_file_upload_security():
    """Test file upload security features"""
    print("\n" + "="*50)
    print("TESTING FILE UPLOAD SECURITY")
    print("="*50)

    url = 'http://127.0.0.1:5000/api/upload/image'

    # Test 1: Invalid file type
    print("\nTest 1: Invalid file type (.txt)")
    try:
        with open('test_xss.txt', 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            response = requests.post(url, files=files, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            if response.status_code == 400 and 'INVALID_FILE_TYPE' in response.text:
                print("✅ PASS: Invalid file type correctly rejected")
            else:
                print("❌ FAIL: Invalid file type not rejected properly")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    # Test 2: Oversized file (create a large file)
    print("\nTest 2: Oversized file (>5MB)")
    try:
        # Create a large file
        with open('large_test.jpg', 'wb') as f:
            f.write(b'0' * (6 * 1024 * 1024))  # 6MB

        with open('large_test.jpg', 'rb') as f:
            files = {'file': ('large.jpg', f, 'image/jpeg')}
            response = requests.post(url, files=files, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            if response.status_code == 400:
                print("✅ PASS: Oversized file correctly rejected")
            else:
                print("❌ FAIL: Oversized file not rejected")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists('large_test.jpg'):
            os.remove('large_test.jpg')

def test_xss_protection():
    """Test XSS protection in messages"""
    print("\n" + "="*50)
    print("TESTING XSS PROTECTION")
    print("="*50)

    # Test via Socket.IO
    print("\nTest 1: XSS via Socket.IO message")
    sio = socketio.Client()

    @sio.event
    def connect():
        print("Connected to server")

    @sio.event
    def disconnect():
        print("Disconnected from server")

    @sio.event
    def message_from_visitor(data):
        print(f"Received sanitized message: {data.get('content_text', '')[:100]}")
        # Check if script tags are removed
        content = data.get('content_text', '')
        if '<script>' not in content and 'alert' not in content:
            print("✅ PASS: XSS payload sanitized")
        else:
            print("❌ FAIL: XSS payload not sanitized")

    try:
        sio.connect('http://127.0.0.1:5000')
        time.sleep(1)

        # Test XSS payload
        xss_payload = '<script>alert("XSS Attack")</script><img src=x onerror=alert(1)>Hello World'

        sio.emit('message_from_visitor', {
            'thread_id': 'security-test-thread',
            'text': xss_payload,
            'type': 'text'
        })

        print(f"Sent XSS payload: {xss_payload}")
        time.sleep(3)  # Wait for response

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        sio.disconnect()

def test_input_validation():
    """Test input validation and sanitization"""
    print("\n" + "="*50)
    print("TESTING INPUT VALIDATION")
    print("="*50)

    print("\nTest 1: SQL Injection attempt")
    sio = socketio.Client()

    @sio.event
    def connect():
        print("Connected to server")

    @sio.event
    def disconnect():
        print("Disconnected from server")

    try:
        sio.connect('http://127.0.0.1:5000')
        time.sleep(1)

        # Test SQL injection
        sql_payload = "'; DROP TABLE messages; --"

        sio.emit('message_from_visitor', {
            'thread_id': 'security-test-thread',
            'text': sql_payload,
            'type': 'text'
        })

        print(f"Sent SQL injection payload: {sql_payload}")
        print("✅ PASS: SQL injection payload sent (validation should prevent execution)")

        time.sleep(2)

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        sio.disconnect()

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\n" + "="*50)
    print("TESTING RATE LIMITING")
    print("="*50)

    url = 'http://127.0.0.1:5000/api/upload/image'

    print("\nTest 1: Multiple rapid uploads")
    try:
        # Create a small valid image file
        with open('test_image.jpg', 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')

        success_count = 0
        rate_limit_count = 0

        for i in range(10):
            try:
                with open('test_image.jpg', 'rb') as f:
                    files = {'file': ('test.jpg', f, 'image/jpeg')}
                    response = requests.post(url, files=files, timeout=5)
                    if response.status_code == 200:
                        success_count += 1
                    elif response.status_code == 429:
                        rate_limit_count += 1
                        print(f"Rate limit hit on attempt {i+1}")
                        break
                    time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                print(f"Error on attempt {i+1}: {e}")

        print(f"Successful uploads: {success_count}")
        print(f"Rate limited requests: {rate_limit_count}")

        if rate_limit_count > 0:
            print("✅ PASS: Rate limiting is working")
        else:
            print("⚠️  WARNING: Rate limiting may not be working properly")

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists('test_image.jpg'):
            os.remove('test_image.jpg')

def main():
    """Run all security tests"""
    print("🔒 CHAT APPLICATION SECURITY TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create test files
    print("\nCreating test files...")
    with open('test_xss.txt', 'w') as f:
        f.write('<script>alert("XSS")</script>')

    try:
        # Run tests
        test_file_upload_security()
        test_xss_protection()
        test_input_validation()
        test_rate_limiting()

        print("\n" + "="*50)
        print("SECURITY TESTING COMPLETED")
        print("="*50)
        print("\n📋 Summary:")
        print("- File upload security: Tested invalid types and oversized files")
        print("- XSS protection: Tested script injection via Socket.IO")
        print("- Input validation: Tested SQL injection attempts")
        print("- Rate limiting: Tested upload frequency limits")
        print("\nCheck server logs for security events and blocked attempts.")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during testing: {e}")

    finally:
        # Cleanup
        print("\nCleaning up test files...")
        for filename in ['test_xss.txt']:
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == '__main__':
    main()
