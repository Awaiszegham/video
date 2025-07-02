#!/usr/bin/env python3
"""
Test script for the Audio/Video Processing API
"""

import requests
import json
import time
import os
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_storage_info():
    """Test storage information endpoint"""
    print("Testing storage info...")
    try:
        response = requests.get(f"{BASE_URL}/storage/info")
        assert response.status_code == 200
        data = response.json()
        assert "storage_type" in data
        print(f"✅ Storage info: {data['storage_type']}")
        return True
    except Exception as e:
        print(f"❌ Storage info failed: {e}")
        return False

def test_list_files():
    """Test file listing endpoint"""
    print("Testing file listing...")
    try:
        response = requests.get(f"{BASE_URL}/files")
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        print(f"✅ File listing: {len(data['files'])} files found")
        return True
    except Exception as e:
        print(f"❌ File listing failed: {e}")
        return False

def test_ai_languages():
    """Test AI languages endpoint"""
    print("Testing AI languages...")
    try:
        response = requests.get(f"{BASE_URL}/ai/languages")
        # This might fail if Google Translate is not configured, which is expected
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI languages: {len(data.get('languages', []))} languages")
        else:
            print("⚠️ AI languages endpoint not available (Google Translate not configured)")
        return True
    except Exception as e:
        print(f"⚠️ AI languages test: {e}")
        return True  # Not critical for basic functionality

def test_whisper_models():
    """Test Whisper model availability"""
    print("Testing Whisper model availability...")
    try:
        import whisper
        models = whisper.available_models()
        print(f"✅ Whisper models available: {models}")
        return True
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("Testing FFmpeg...")
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg available: {version_line}")
            return True
        else:
            print("❌ FFmpeg not working properly")
            return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def test_sox():
    """Test SoX availability"""
    print("Testing SoX...")
    try:
        import subprocess
        result = subprocess.run(['sox', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print(f"✅ SoX available: {version_line}")
            return True
        else:
            print("❌ SoX not working properly")
            return False
    except Exception as e:
        print(f"❌ SoX test failed: {e}")
        return False

def test_redis():
    """Test Redis connectivity"""
    print("Testing Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def test_celery_import():
    """Test Celery configuration"""
    print("Testing Celery import...")
    try:
        from celery_app import celery_app
        print(f"✅ Celery app configured: {celery_app.main}")
        return True
    except Exception as e:
        print(f"❌ Celery import failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting API Tests\n")
    
    tests = [
        ("System Dependencies", [
            test_ffmpeg,
            test_sox,
            test_redis,
        ]),
        ("Python Components", [
            test_whisper_models,
            test_celery_import,
        ]),
        ("API Endpoints", [
            test_health_check,
            test_storage_info,
            test_list_files,
            test_ai_languages,
        ])
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for category, test_functions in tests:
        print(f"\n📋 {category}")
        print("-" * 40)
        
        for test_func in test_functions:
            total_tests += 1
            if test_func():
                passed_tests += 1
            time.sleep(0.5)  # Small delay between tests
    
    print(f"\n📊 Test Results")
    print("=" * 40)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed!")
    elif passed_tests >= total_tests * 0.8:
        print("\n✅ Most tests passed - system is functional")
    else:
        print("\n⚠️ Several tests failed - check configuration")
    
    return passed_tests, total_tests

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print("✅ Server is running, proceeding with tests...")
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server first:")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")

