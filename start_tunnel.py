"""
Nova Apparels - Public Link & Tunnel Launcher
Generates a secure HTTPS public link using Cloudflare Tunnel and saves it to SHAREABLE_LINK.txt
"""

import os
import sys
import subprocess
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED = os.path.join(BASE_DIR, "bin", "cloudflared.exe")
LINK_FILE = os.path.join(BASE_DIR, "SHAREABLE_LINK.txt")

if not os.path.exists(CLOUDFLARED):
    print("[ERROR] cloudflared.exe not found in bin directory.")
    sys.exit(1)

print("\n=======================================================")
print("   NOVA APPARELS - SECURE PARTNER PUBLIC LINK GENERATOR")
print("=======================================================\n")
print("Connecting to Cloudflare Network...")

cmd = [CLOUDFLARED, "tunnel", "--url", "http://127.0.0.1:8765"]
proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

url_found = None
start_time = time.time()

while time.time() - start_time < 25:
    line = proc.stderr.readline()
    if not line:
        time.sleep(0.1)
        continue
    
    # search for trycloudflare.com url
    match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
    if match:
        url_found = match.group(1)
        break

if url_found:
    with open(LINK_FILE, "w", encoding="utf-8") as f:
        f.write(f"NOVA APPARELS - 24/7 PARTNER LIVE PORTAL\n")
        f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"SHAREABLE LINK FOR ARSH, KIRAN & ANURAG:\n")
        f.write(f"{url_found}\n\n")
        f.write(f"Note: This link works on Mobile, iPhone, Android, and PC anywhere without login.\n")
    
    print("\n-------------------------------------------------------")
    print(f" SUCCESS! Your Public Partner Link is Ready:")
    print(f" >>> {url_found} <<<")
    print("-------------------------------------------------------")
    print(f" Saved to: {LINK_FILE}")
    print(" Share this link directly on WhatsApp/Telegram with Kiran and Anurag!")
    print(" Keep this window open so the link stays active.\n")
else:
    print("[NOTICE] Cloudflare tunnel started. Check logs for link.")

try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
