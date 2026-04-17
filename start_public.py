"""
start_public.py — Share the chatbot with anyone while your laptop is running.

Usage:
    python start_public.py

What it does:
    1. Builds the React frontend (skips if already up to date)
    2. Starts the FastAPI backend on localhost:8000
    3. Opens a public ngrok tunnel
    4. Prints a URL you can share with up to 10 people

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
import subprocess
import sys
import threading
import time
from pathlib import Path

# Force UTF-8 output so box-drawing characters work on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
BUILD_DIR    = FRONTEND_DIR / "build"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print(msg: str, colour: str = "") -> None:
    codes = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "bold": "\033[1m", "": ""}
    print(f"{codes[colour]}{msg}\033[0m")


def _build_needed() -> bool:
    """Return True if the React build is missing or older than any src file."""
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
    """Kill any process currently listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, shell=True,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, shell=True)
                _print(f"  Freed port {port} (killed PID {pid}).", "yellow")
    except Exception:
        pass


def start_backend(port: int) -> None:
    """Run uvicorn in a background daemon thread."""
    _free_port(port)
    def _run():
        uvicorn.run(
            "backend.api:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
            workers=1,
        )
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def start_tunnel(port: int) -> str:
    """Open an ngrok tunnel and return the public HTTPS URL."""
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        _print("\n  pyngrok not installed. Run:  pip install pyngrok\n", "red")
        sys.exit(1)

    # Use NGROK_AUTHTOKEN from .env if set
    token = os.getenv("NGROK_AUTHTOKEN")
    if token:
        conf.get_default().auth_token = token

    # Kill any leftover ngrok process from a previous run
    try:
        ngrok.kill()
    except Exception:
        pass
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"],
                       capture_output=True, shell=True)
    except Exception:
        pass
    time.sleep(2)

    tunnel = ngrok.connect(port, "http")
    return tunnel.public_url.replace("http://", "https://")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    PORT = 8000

    _print("\n╔══════════════════════════════════════════════╗", "bold")
    _print("║   Bradford Council Chatbot — Public Mode     ║", "bold")
    _print("╚══════════════════════════════════════════════╝\n", "bold")

    # 1. Build frontend
    _print("Step 1/3 — Frontend", "bold")
    build_frontend()

    # 2. Start backend
    _print("\nStep 2/3 — Backend", "bold")
    _print(f"  Starting FastAPI on port {PORT}...", "yellow")
    start_backend(PORT)
    time.sleep(2)   # give uvicorn time to bind
    _print("  Backend is running.", "green")

    # 3. Open tunnel
    _print("\nStep 3/3 — Public tunnel", "bold")
    _print("  Opening ngrok tunnel...", "yellow")
    public_url = start_tunnel(PORT)

    # 4. Print share URL
    _print("\n" + "═" * 52, "bold")
    _print("  SHARE THIS LINK:", "bold")
    _print(f"\n      {public_url}\n", "green")
    _print("  Up to 10 people can open this in any browser.", "")
    _print("  The link works as long as this window is open.", "")
    _print("═" * 52, "bold")
    _print("\n  Press Ctrl+C to stop.\n", "yellow")

    # 5. Keep alive
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        _print("\n  Shutting down...", "yellow")
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except Exception:
            pass
        _print("  Done. The public URL is no longer active.\n", "green")


if __name__ == "__main__":
    # Make sure we run from the project root
    os.chdir(ROOT)
    # Load .env so OPENAI_API_KEY and NGROK_AUTHTOKEN are available
    from dotenv import load_dotenv
    load_dotenv()
    main()
