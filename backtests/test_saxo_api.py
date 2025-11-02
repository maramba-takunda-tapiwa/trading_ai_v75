"""Test Saxo API endpoints to find the right format"""
import requests
import json
import os
import sys

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

print("🔍 Testing Saxo API Endpoints...\n")

# Test 1: Get account balance
print("=" * 70)
print("TEST 1: Get Account Balance")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/port/v1/balances"
    params = {'ClientKey': ACCOUNT_ID}
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Balance data:\n{json.dumps(data, indent=2)[:500]}")
    else:
        print(f"❌ Error: {response.text[:300]}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Get current price (InfoPrices)
print("\n" + "=" * 70)
print("TEST 2: Get Current Price (EUR/USD, UIC=21)")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/trade/v1/infoprices"
    params = {'AssetType': 'FxSpot', 'Uic': 21}
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Price data:\n{json.dumps(data, indent=2)[:500]}")
    else:
        print(f"❌ Error: {response.text[:300]}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 3: Get historical chart data
print("\n" + "=" * 70)
print("TEST 3: Get Historical Chart Data (EUR/USD, 1H)")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/chart/v1/charts"
    params = {
        'AssetType': 'FxSpot',
        'Uic': 21,
        'Horizon': 60,  # 1 hour
        'Count': 50
    }
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Chart data:\n{json.dumps(data, indent=2)[:800]}")
    else:
        print(f"❌ Error: {response.text[:300]}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 4: Search for instrument details
print("\n" + "=" * 70)
print("TEST 4: Search for EUR/USD Instrument")
print("=" * 70)
try:
    endpoint = f"{BASE_URL}/ref/v1/instruments"
    params = {
        'AssetTypes': 'FxSpot',
        'Keywords': 'EURUSD',
        '$top': 5
    }
    response = requests.get(endpoint, headers=HEADERS, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Instrument data:\n{json.dumps(data, indent=2)[:800]}")
    else:
        print(f"❌ Error: {response.text[:300]}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 70)
print("API TESTING COMPLETE")
print("=" * 70)
