#!/usr/bin/env python3
"""
Test script to verify chat endpoint works with model selection
"""

import requests

BASE_URL = "http://192.168.1.4:8000"


def test_chat():
    """Test the /api/chat endpoint with model selection"""

    # First, login to get session
    print("1. Testing login...")
    login_response = requests.post(
        f"{BASE_URL}/api/login",
        json={"email": "muhammadfathul386@gmail.com", "password": "Password@123"},
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return False

    print("✅ Login successful")

    # Now test chat with OpenAI model
    print("\n2. Testing chat with OpenAI (gpt-4o-mini)...")
    chat_response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "Berapa total pengeluaran saya bulan lalu?",
            "model_provider": "openai",
            "model": "gpt-4o-mini",
            "lang": "id",
        },
    )

    print(f"Status: {chat_response.status_code}")
    if chat_response.status_code == 200:
        result = chat_response.json()
        print("✅ OpenAI chat successful")
        print(f"Response: {result.get('answer', '')[:100]}...")
    else:
        print("❌ OpenAI chat failed")
        print(chat_response.text)
        return False

    # Test chat with Google model
    print("\n3. Testing chat with Google (gemini-2.5-flash)...")
    chat_response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "Apa saja kategori pengeluaran saya?",
            "model_provider": "google",
            "model": "gemini-2.5-flash",
            "lang": "id",
        },
    )

    print(f"Status: {chat_response.status_code}")
    if chat_response.status_code == 200:
        result = chat_response.json()
        print("✅ Google chat successful")
        print(f"Response: {result.get('answer', '')[:100]}...")
    else:
        print("❌ Google chat failed")
        print(chat_response.text)
        return False

    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_chat()
