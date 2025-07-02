#!/usr/bin/env python3
"""
Integration test for the Audio/Video Processing API
Tests basic functionality without external services
"""

import os
import time
import subprocess
import signal
import requests
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_AUDIO_FILE = "uploads/test_audio.wav"

class APITester:
    def __init__(self):
        self.server_process = None
        self.passed_tests = 0
        self.total_tests = 0
    
    def start_server(self):
        """Start the FastAPI server in background"""
        print("🚀 Starting FastAPI server...")
        try:
            self.server_process = subprocess.Popen([
                "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            for i in range(10):
                try:
                    response = requests.get(f"{BASE_URL}/", timeout=1)
                    if response.status_code == 200:
                        print("✅ Server started successfully")
                        return True
                except:
                    time.sleep(1)
            
            print("❌ Server failed to start")
            return False
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def stop_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
    
    def run_test(self, test_name, test_func):
        """Run a single test"""
        print(f"Testing {test_name}...")
        self.total_tests += 1
        try:
            if test_func():
                print(f"✅ {test_name} passed")
                self.passed_tests += 1
                return True
            else:
                print(f"❌ {test_name} failed")
                return False
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            return False
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/")
        return response.status_code == 200 and "message" in response.json()
    
    def test_file_listing(self):
        """Test file listing"""
        response = requests.get(f"{BASE_URL}/files")
        return response.status_code == 200 and "files" in response.json()
    
    def test_storage_info(self):
        """Test storage information"""
        response = requests.get(f"{BASE_URL}/storage/info")
        data = response.json()
        return response.status_code == 200 and data.get("storage_type") == "local"
    
    def test_audio_file_exists(self):
        """Test that test audio file exists"""
        return os.path.exists(TEST_AUDIO_FILE)
    
    def test_ffmpeg_info(self):
        """Test FFmpeg functionality"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(TEST_AUDIO_FILE)
            return "streams" in probe and len(probe["streams"]) > 0
        except:
            return False
    
    def test_whisper_basic(self):
        """Test Whisper model loading"""
        try:
            import whisper
            # Just test that we can load the tiny model
            model = whisper.load_model("tiny")
            return model is not None
        except:
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Running Integration Tests")
        print("=" * 50)
        
        # Start server
        if not self.start_server():
            return False
        
        try:
            # Run tests
            tests = [
                ("Health Check", self.test_health_check),
                ("File Listing", self.test_file_listing),
                ("Storage Info", self.test_storage_info),
                ("Test Audio File", self.test_audio_file_exists),
                ("FFmpeg Integration", self.test_ffmpeg_info),
                ("Whisper Basic", self.test_whisper_basic),
            ]
            
            for test_name, test_func in tests:
                self.run_test(test_name, test_func)
                time.sleep(0.5)
            
            # Results
            print("\n📊 Integration Test Results")
            print("=" * 50)
            print(f"Total tests: {self.total_tests}")
            print(f"Passed: {self.passed_tests}")
            print(f"Failed: {self.total_tests - self.passed_tests}")
            print(f"Success rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
            
            if self.passed_tests == self.total_tests:
                print("\n🎉 All integration tests passed!")
                print("The application is ready for deployment!")
            elif self.passed_tests >= self.total_tests * 0.8:
                print("\n✅ Most tests passed - application is functional")
            else:
                print("\n⚠️ Several tests failed - check configuration")
            
            return self.passed_tests >= self.total_tests * 0.8
            
        finally:
            self.stop_server()

def main():
    """Main test function"""
    print("🔧 Audio/Video Processing API - Integration Tests")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Please run this script from the project root directory")
        return False
    
    # Activate virtual environment check
    try:
        import fastapi
        import celery
        import whisper
        print("✅ Virtual environment and dependencies OK")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please activate the virtual environment and install requirements")
        return False
    
    # Run tests
    tester = APITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 Ready for deployment!")
        print("\nNext steps:")
        print("1. Configure external services (Google Cloud, Cloudflare R2)")
        print("2. Set up environment variables")
        print("3. Deploy using Docker or Railway")
        print("4. Set up n8n for workflow automation")
    
    return success

if __name__ == "__main__":
    main()

