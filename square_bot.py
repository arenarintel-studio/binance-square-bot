import requests
import time
import hashlib
import hmac
import json
import random
from datetime import datetime

# === CONFIG - SET THESE ===
API_KEY = "YOUR_API_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"

def create_signature(query_string, secret):
    """Create signature for Binance API"""
    return hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def post_to_square(content):
    """Simple working post function"""
    base_url = "https://www.binance.com/bapi/square/v1/public/square/post/create"
    
    # Create timestamp and signature
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string, SECRET_KEY)
    
    # Prepare headers
    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Prepare post content
    payload = {
        "content": content,
        "contentType": "text",
        "language": "en"
    }
    
    # Full URL with signature
    url = f"{base_url}?{query_string}&signature={signature}"
    
    # Send post
    print(f"Posting: {content[:50]}...")
    response = requests.post(url, headers=headers, json=payload)
    
    # Print result
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response.json()

# === SIMPLE TEST ===
if name == "__main__":
    # Simple test message
    test_message = f"Testing my new crypto bot! 🤖 #{random.randint(1000,9999)}"
    
    result = post_to_square(test_message)
    print("Done!")
