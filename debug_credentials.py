#!/usr/bin/env python
"""
Debug Vonage Credentials
Run this to find out exactly what's wrong
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'westPoint.settings')
django.setup()

from django.conf import settings
import requests

print("=" * 60)
print("VONAGE CREDENTIALS DEBUG")
print("=" * 60)

# 1. Check if settings exist
print("\n1. SETTINGS EXISTENCE")
has_key = hasattr(settings, 'VONAGE_API_KEY')
has_secret = hasattr(settings, 'VONAGE_API_SECRET')
has_enabled = hasattr(settings, 'SMS_ENABLED')

print(f"   VONAGE_API_KEY: {'✅ Exists' if has_key else '❌ Missing'}")
print(f"   VONAGE_API_SECRET: {'✅ Exists' if has_secret else '❌ Missing'}")
print(f"   SMS_ENABLED: {'✅ Exists' if has_enabled else '❌ Missing'}")

if not (has_key and has_secret):
    print("\n❌ Settings not configured!")
    print("Add to settings.py:")
    print("VONAGE_API_KEY = 'your_key'")
    print("VONAGE_API_SECRET = 'your_secret'")
    sys.exit(1)

# 2. Get values
api_key = settings.VONAGE_API_KEY
api_secret = settings.VONAGE_API_SECRET

print("\n2. SETTINGS VALUES")
print(f"   API Key: '{api_key}'")
print(f"   API Secret: '{api_secret}'")

# 3. Check types
print("\n3. VALUE TYPES")
print(f"   API Key type: {type(api_key).__name__}")
print(f"   API Secret type: {type(api_secret).__name__}")

if not isinstance(api_key, str):
    print(f"   ⚠️ API Key should be string, got {type(api_key)}")
if not isinstance(api_secret, str):
    print(f"   ⚠️ API Secret should be string, got {type(api_secret)}")

# 4. Check lengths
print("\n4. LENGTH CHECK")
print(f"   API Key length: {len(api_key)} (should be 8)")
print(f"   API Secret length: {len(api_secret)} (should be 16-18)")

if len(api_key) != 8:
    print(f"   ⚠️ API Key wrong length!")
if len(api_secret) < 16 or len(api_secret) > 20:
    print(f"   ⚠️ API Secret wrong length!")

# 5. Check for whitespace
print("\n5. WHITESPACE CHECK")
if api_key != api_key.strip():
    print(f"   ⚠️ API Key has leading/trailing spaces!")
    print(f"   Before strip: '{api_key}'")
    print(f"   After strip: '{api_key.strip()}'")
else:
    print(f"   ✅ API Key: No whitespace issues")

if api_secret != api_secret.strip():
    print(f"   ⚠️ API Secret has leading/trailing spaces!")
    print(f"   Before strip: '{api_secret}'")
    print(f"   After strip: '{api_secret.strip()}'")
else:
    print(f"   ✅ API Secret: No whitespace issues")

# 6. Check for special characters
print("\n6. CHARACTER CHECK")
print(f"   API Key bytes: {api_key.encode()}")
print(f"   API Secret bytes: {api_secret.encode()}")

# 7. Test with Vonage directly
print("\n7. VONAGE API TEST")
print("   Testing with current credentials...")

try:
    url = "https://rest.nexmo.com/account/get-balance"
    params = {
        'api_key': api_key.strip(),
        'api_secret': api_secret.strip()
    }
    
    response = requests.get(url, params=params, timeout=10)
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code == 200:
        print("   ✅ Credentials are CORRECT!")
        data = response.json()
        print(f"   Balance: €{data.get('value', 0)}")
    elif response.status_code == 401:
        print("   ❌ Credentials are WRONG!")
        print("\n   STEPS TO FIX:")
        print("   1. Go to https://dashboard.nexmo.com/")
        print("   2. Look at TOP of page for API Key and Secret")
        print("   3. Copy them EXACTLY (no spaces, no extra quotes)")
        print("   4. Update settings.py:")
        print(f"      VONAGE_API_KEY = 'paste_key_here'")
        print(f"      VONAGE_API_SECRET = 'paste_secret_here'")
        print("   5. Restart Django (Ctrl+C then start again)")
        print("   6. Run this script again")
    else:
        print(f"   ⚠️ Unexpected status code: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 8. Compare with what you should enter
print("\n8. WHAT YOU SHOULD ENTER IN SETTINGS.PY")
print("=" * 60)
print("# In settings.py, it should look like this:")
print(f"VONAGE_API_KEY = 'xxxxxxxx'  # ← 8 characters, no spaces")
print(f"VONAGE_API_SECRET = 'xxxxxxxxxxxxxxxxxx'  # ← 16-18 chars, no spaces")
print("SMS_ENABLED = True")
print("=" * 60)

print("\n9. CURRENT SETTINGS IN YOUR FILE")
print("=" * 60)
print(f"VONAGE_API_KEY = '{api_key}'")
print(f"VONAGE_API_SECRET = '{api_secret}'")
print(f"SMS_ENABLED = {settings.SMS_ENABLED}")
print("=" * 60)

print("\nDEBUG COMPLETE")
print("=" * 60)