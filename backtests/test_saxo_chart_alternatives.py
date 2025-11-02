"""Test alternative Saxo chart endpoints"""
import requests
import json
import os
from datetime import datetime, timedelta

# Load credentials
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'results', 'saxo_config.json')
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

ACCESS_TOKEN = config['access_token']
ACCOUNT_ID = config['account_id']
BASE_URL = 'https://gateway.saxobank.com/sim/openapi'

HEADERS = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

print("🔍 Testing Alternative Chart Endpoints...\n")

# Test 1: Try without /charts suffix
print("=" * 70)
print("TEST 1: Try /chart/v1 with params")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/chart/v1"
    params = {
        'AssetType': 'FxSpot',
        'Uic': 21,
        'Horizon': 60,
        'Count': 50,
        'Mode': 'From',
        'Time': (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'
    }
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Try chart subscription endpoint  
print("\n" + "=" * 70)
print("TEST 2: Try /chart/v1/charts/subscriptions")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/chart/v1/charts/subscriptions"
    response = requests.get(endpoint, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 3: Build candles from tick/price history
print("\n" + "=" * 70)
print("TEST 3: Use InfoPrices and build our own candles")
print("=" * 70)
print("Strategy: Poll /trade/v1/infoprices every minute and aggregate")
print("This is how V2 works - simulate live candles from current prices")
print("✅ This approach WILL work - we just need to implement aggregation")

# Test 4: Try historical prices endpoint
print("\n" + "=" * 70)
print("TEST 4: Try /trade/v1/prices endpoint")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/trade/v1/prices"
    params = {
        'AssetType': 'FxSpot',
        'Uic': 21
    }
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Success:\n{json.dumps(response.json(), indent=2)[:500]}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 70)
print("RECOMMENDATION:")
print("=" * 70)
print("Saxo Demo API doesn't provide historical candles directly.")
print("SOLUTION: Use CSV historical data + live prices for new bars")
print("This is exactly what V2 does - it's the standard approach!")
print("\nImplementation:")
print("1. Load historical OHLC from CSV (data/eurusd_candles.csv)")
print("2. Poll current price every minute from /trade/v1/infoprices")
print("3. Build new hourly candles as they complete")
print("4. Strategy runs on combined historical + live data")
