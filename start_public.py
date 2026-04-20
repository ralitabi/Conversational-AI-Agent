"""
start_public.py — Share the chatbot with anyone while your laptop is running.

Usage:
    python start_public.py

What it does:
    1. Builds the React frontend (skips if already up to date)
    2. Starts the FastAPI backend on localhost:8000
    3. Opens a public tunnel (tries ngrok → cloudflared → localtunnel)
    4. Prints a URL you can share

Requirements:
    pip install pyngrok
    A free ngrok account token (one-time setup — see below)

First-time ngrok setup (free):
    1. Sign up at https://ngrok.com  (free)
    2. Copy your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
    3. Run once:  ngrok config add-authtoken <your-token>
       OR set env var:  NGROK_AUTHTOKEN=<your-token> in your .env file
"""

import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

# Force UTF-8 output so box-drawing characters work on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn

ROOT         = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
BUILD_DIR    = FRONTEND_DIR / "build"

# Keep tunnel subprocess alive for the lifetime of the script
_tunnel_proc = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print(msg: str, colour: str = "") -> None:
    codes = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "bold": "\033[1m", "": ""}
    print(f"{codes[colour]}{msg}\033[0m")


def _build_needed() -> bool:
    index = BUILD_DIR / "index.html"
    if not index.exists():
        return True
    build_time = index.stat().st_mtime
    for f in (FRONTEND_DIR / "src").rglob("*"):
        if f.is_file() and f.stat().st_mtime > build_time:
            return True
    return False


def build_frontend() -> None:
    if not _build_needed():
        _print("  Frontend build is up to date — skipping npm build.", "green")
        return
    _print("  Building React frontend (this takes ~30 seconds)...", "yellow")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=False,
        shell=sys.platform == "win32",
    )
    if result.returncode != 0:
        _print("  ERROR: npm run build failed. Is Node installed?", "red")
        sys.exit(1)
    _print("  Frontend build complete.", "green")


def _free_port(port: int) -> None:
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, shell=True)
        killed = False
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, shell=True)
                _print(f"  Freed port {port} (killed PID {pid}).", "yellow")
                killed = True
        if killed:
            time.sleep(2)  # wait for OS to release the port
    except Exception:
        pass


def _wait_for_backend(port: int, timeout: int = 15) -> bool:
    """Return True once the backend responds on the given port."""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def start_backend(port: int) -> None:
    _free_port(port)
    def _run():
        uvicorn.run("backend.api:app", host="127.0.0.1", port=port,
                    log_level="warning", workers=1)
    threading.Thread(target=_run, daemon=True).start()
    if not _wait_for_backend(port):
        _print(f"  ERROR: Backend did not start on port {port}.", "red")
        sys.exit(1)


def _public_ip() -> str:
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except Exception:
        return ""


# ── Tunnel providers ──────────────────────────────────────────────────────────

def _try_ngrok(port: int) -> str | None:
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        return None

    token = os.getenv("NGROK_AUTHTOKEN")
    if token:
        conf.get_default().auth_token = token

    try:
        ngrok.kill()
    except Exception:
        pass
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True, shell=True)
    except Exception:
        pass
    time.sleep(2)

    for attempt in range(1, 4):
        try:
            tunnel = ngrok.connect(port, "http")
            return tunnel.public_url.replace("http://", "https://")
        except Exception as exc:
            _print(f"  ngrok attempt {attempt}/3 failed: {exc}", "yellow")
            try:
                ngrok.kill()
            except Exception:
                pass
            time.sleep(4)
    return None


def _try_cloudflared(port: int) -> str | None:
    """Use cloudflared quick tunnel — no account, no password page."""
    global _tunnel_proc

    # Use bundled exe next to this script, or fall back to PATH
    bundled = ROOT / "cloudflared.exe"
    if bundled.exists():
        exe = str(bundled)
    else:
        which = subprocess.run(
            ["where", "cloudflared"] if sys.platform == "win32" else ["which", "cloudflared"],
            capture_output=True, text=True, shell=sys.platform == "win32",
        )
        if which.returncode != 0:
            return None
        exe = "cloudflared"

    _print("  Trying cloudflared...", "yellow")
    try:
        proc = subprocess.Popen(
            [exe, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _tunnel_proc = proc
        found_url = None

        for _ in range(60):
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break  # process died
                time.sleep(0.5)
                continue
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                found_url = match.group(0)
                break

        if not found_url:
            return None

        # Drain stdout in background so the pipe never fills up and kills the process
        def _drain(p):
            try:
                for _ in p.stdout:
                    pass
            except Exception:
                pass

        threading.Thread(target=_drain, args=(proc,), daemon=True).start()
        return found_url

    except Exception as exc:
        _print(f"  cloudflared failed: {exc}", "yellow")
        return None


def _try_localtunnel(port: int) -> tuple[str, str] | tuple[None, None]:
    """
    Fall back to localtunnel via npx.
    Returns (url, tunnel_password) — visitors must enter the password on first visit.
    """
    global _tunnel_proc
    _print("  Trying localtunnel as fallback...", "yellow")
    try:
        proc = subprocess.Popen(
            ["npx", "--yes", "localtunnel", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=sys.platform == "win32",
        )
        _tunnel_proc = proc
        for _ in range(60):
            line = proc.stdout.readline()
            if not line:
                time.sleep(1)
                continue
            match = re.search(r"https?://\S+", line)
            if match:
                url = match.group(0).rstrip(".").replace("http://", "https://")
                password = _public_ip()
                return url, password
        return None, None
    except Exception as exc:
        _print(f"  localtunnel failed: {exc}", "yellow")
        return None, None


def start_tunnel(port: int) -> tuple[str, str]:
    """
    Try each tunnel provider in order.
    Returns (public_url, tunnel_password).
    tunnel_password is empty string for ngrok/cloudflared (no password needed).
    """
    _print("  Trying ngrok...", "yellow")
    url = _try_ngrok(port)
    if url:
        return url, ""

    url = _try_cloudflared(port)
    if url:
        return url, ""

    _print("  ngrok blocked — switching to localtunnel (no account needed).", "yellow")
    url, password = _try_localtunnel(port)
    if url:
        return url, password or ""

    _print("\n  All tunnel providers failed.", "red")
    _print("  Your network may be blocking tunnel services.", "red")
    _print("  Try running on a different network (e.g. mobile hotspot).\n", "red")
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    PORT = 8000

    _print("\n╔══════════════════════════════════════════════╗", "bold")
    _print("║   Bradford Council Chatbot — Public Mode     ║", "bold")
    _print("╚══════════════════════════════════════════════╝\n", "bold")

    _print("Step 1/3 — Frontend", "bold")
    build_frontend()

    _print("\nStep 2/3 — Backend", "bold")
    _print(f"  Starting FastAPI on port {PORT}...", "yellow")
    start_backend(PORT)
    time.sleep(2)
    _print("  Backend is running.", "green")

    _print("\nStep 3/3 — Public tunnel", "bold")
    public_url, tunnel_password = start_tunnel(PORT)

    _print("\n" + "═" * 52, "bold")
    _print("  SHARE THIS LINK:", "bold")
    _print(f"\n      {public_url}\n", "green")

    if tunnel_password:
        _print("  ⚠  Visitors will see a password page on first open.", "yellow")
        _print(f"  Tell them to enter this password:  {tunnel_password}", "yellow")
        _print("  (This is your public IP — it acts as a one-time gate.)\n", "")

    _print("  The link works as long as this window is open.", "")
    _print("═" * 52, "bold")
    _print("\n  Press Ctrl+C to stop.\n", "yellow")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        _print("\n  Shutting down...", "yellow")
        if _tunnel_proc:
            try:
                _tunnel_proc.terminate()
            except Exception:
                pass
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except Exception:
            pass
        _print("  Done. The public URL is no longer active.\n", "green")


if __name__ == "__main__":
    os.chdir(ROOT)
    from dotenv import load_dotenv
    load_dotenv()
    main()
