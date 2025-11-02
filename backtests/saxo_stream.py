"""
Simple streaming shim for Saxo REST vs streaming API.
If streaming credentials are configured, this module should provide a `get_price()` method that returns a dict like:
{'time': datetime, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': int}

This is a minimal placeholder that currently falls back to polling and can be extended to use websockets streaming if you provide credentials.
"""
from datetime import datetime
import requests

BASE_URL = 'https://gateway.saxobank.com/sim/openapi'
HEADERS = {}

def configure(headers):
    global HEADERS
    HEADERS = headers


def get_price_fxspot(uic=21):
    """Poll a single FX spot quote (fallback)."""
    try:
        response = requests.get(f'{BASE_URL}/trade/v1/infoprices?AssetType=FxSpot&Uic={uic}', headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data['Quote']['Mid']
            timestamp = datetime.utcnow()
            return {'time': timestamp, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': 1}
    except Exception:
        return None
    return None
