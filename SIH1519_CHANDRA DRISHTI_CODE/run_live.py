import os
import urllib.request
import subprocess
import threading
import time
import sys

def download_cloudflared():
    exe_name = "cloudflared.exe"
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    
    if not os.path.exists(exe_name):
        print("[*] Downloading Cloudflare Tunnel (this is a one-time setup)...")
        try:
            urllib.request.urlretrieve(url, exe_name)
            print("[*] Download complete!")
        except Exception as e:
            print(f"[!] Failed to download cloudflared: {e}")
            sys.exit(1)

def run_tunnel():
    print("[*] Starting Cloudflare Tunnel...")
    # Run cloudflared and pipe output to console so the user can see the URL
    process = subprocess.Popen(
        ["cloudflared.exe", "tunnel", "--url", "http://127.0.0.1:5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    url_found = False
    for line in process.stdout:
        print(line, end='')
        if "trycloudflare.com" in line and not url_found:
            print("\n" + "="*70)
            print("YOUR LIVE PUBLIC URL IS IN THE LOGS ABOVE!")
            print("Look for the link ending in .trycloudflare.com")
            print("Share that link with anyone, and it will load your app!")
            print("="*70 + "\n")
            url_found = True

def run_flask():
    print("[*] Starting the AI Backend...")
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    os.chdir(backend_dir)
    subprocess.run([sys.executable, "server.py"])

if __name__ == "__main__":
    print("========================================================")
    print("   CHANDRA DRISHTI - LIVE PUBLIC DEPLOYMENT SCRIPT")
    print("========================================================")
    
    download_cloudflared()
    
    # Start the tunnel in a background thread
    tunnel_thread = threading.Thread(target=run_tunnel, daemon=True)
    tunnel_thread.start()
    
    # Give the tunnel a second to start, then start Flask
    time.sleep(2)
    run_flask()
