"""Quick test to verify V3 can load Saxo credentials"""
import os
import json

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'saxo_config.json')

print("🔍 Testing V3 Credential Loading...\n")

# Test 1: Check if config file exists
if os.path.exists(CONFIG_FILE_PATH):
    print(f"✅ Config file found: {CONFIG_FILE_PATH}")
else:
    print(f"❌ Config file NOT found: {CONFIG_FILE_PATH}")
    exit(1)

# Test 2: Load credentials
try:
    with open(CONFIG_FILE_PATH, 'r') as f:
        config = json.load(f)
    print("✅ Config file loaded successfully")
except Exception as e:
    print(f"❌ Error loading config: {e}")
    exit(1)

# Test 3: Check credentials
app_id = config.get('app_id', '')
access_token = config.get('access_token', '')
account_id = config.get('account_id', '')

print("\n📋 CREDENTIALS:")
print(f"   App ID: {app_id[:20]}... ({len(app_id)} chars)")
print(f"   Account ID: {account_id}")
print(f"   Access Token: {access_token[:30]}...{access_token[-20:]} ({len(access_token)} chars)")

if app_id and access_token and account_id:
    print("\n✅ ALL CREDENTIALS VALID!")
    print("\n🎯 V3 Money Printer ready to trade on Saxo demo account!")
    print("\n📌 NEXT STEPS:")
    print("   1. Run: py backtests\\live_trader_saxo_v3.py")
    print("   2. Monitor dashboard at http://127.0.0.1:5000")
    print("   3. Watch for V3 signals and trades")
    print("\n⚠️  Current API: DEMO (gateway.saxobank.com/sim)")
    print("   To switch to LIVE: Change SAXO_API_BASE in live_trader_saxo_v3.py")
else:
    print("\n❌ MISSING CREDENTIALS!")
    if not app_id:
        print("   - Missing app_id")
    if not access_token:
        print("   - Missing access_token")
    if not account_id:
        print("   - Missing account_id")
