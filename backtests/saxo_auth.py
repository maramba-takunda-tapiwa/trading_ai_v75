import webbrowser
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

# === CONFIG ===
CLIENT_ID = "d9377c5e6a0b4b9aa6e5c81995e95032"
CLIENT_SECRET = "de1db69d02aa45aa8145b0734eb2077a"
REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://sim.logonvalidation.net/authorize"
TOKEN_URL = "https://sim.logonvalidation.net/token"

# === STEP 1: Build auth URL and open browser ===
params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "state": "12345"
}
auth_link = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

print("\n[+] Opening Saxo login page in your browser...")
webbrowser.open(auth_link)

# === STEP 2: Tiny local webserver to catch redirect ===
class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1>You can close this tab.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Error: no code found.</h1>")

def get_auth_code():
    server = HTTPServer(("localhost", 8080), RedirectHandler)
    server.handle_request()
    return getattr(server, "auth_code", None)

auth_code = get_auth_code()
print(f"[+] Got authorization code: {auth_code}")

# === STEP 3: Exchange for token ===
print("[+] Exchanging code for access token...")
data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}
response = requests.post(TOKEN_URL, data=data)
print("\n[+] Token response:")
print(response.json())
