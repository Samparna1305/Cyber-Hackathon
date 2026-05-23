#!/usr/bin/env python3
"""
================================================================
  cert_extractor.py — Certificate Analysis & Pin Extractor
  Hackathon #31: TLS Certificate Pinning Bypass & MitM Attack
  MITRE ATT&CK: T1040 - Network Sniffing
================================================================

PURPOSE:
  1. Connect to the target server and extract its TLS certificate
  2. Compute the SHA-256 SPKI pin (same format as OkHttp uses)
  3. Dump all relevant certificate fields
  4. Optionally extract cert from existing PEM file

USAGE:
  # Live extraction from running server:
  python3 cert_extractor.py --host 10.0.2.2 --port 5000

  # Analyse a saved PEM file:
  python3 cert_extractor.py --pem ../certificates/cert.pem

  # Extract from mitmproxy CA (to install on device):
  python3 cert_extractor.py --mitmproxy-ca ~/.mitmproxy/mitmproxy-ca-cert.pem
================================================================
"""

import ssl
import socket
import hashlib
import base64
import argparse
import datetime
import json
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# ── ANSI colours ─────────────────────────────────────────────
R = "\033[31m"; G = "\033[32m"; Y = "\033[33m"
C = "\033[36m"; B = "\033[34m"; RST = "\033[0m"; BOLD = "\033[1m"

def banner():
    print(f"""
{C}{BOLD}╔══════════════════════════════════════════════════════╗
║   TLS Certificate Extractor & Pin Analyser           ║
║   Hackathon #31 — Attacker Toolchain                 ║
╚══════════════════════════════════════════════════════╝{RST}
""")


# ── Core extraction ───────────────────────────────────────────

def extract_cert_from_server(host: str, port: int) -> bytes:
    """
    Open a raw SSL connection (no verification) and grab the
    DER-encoded server certificate.
    """
    print(f"{Y}[*] Connecting to {host}:{port} (no cert verification)...{RST}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            print(f"{G}[+] TLS handshake complete — cipher: {ssock.cipher()[0]}{RST}")
            der_cert = ssock.getpeercert(binary_form=True)
            return der_cert


def der_to_pem(der: bytes) -> bytes:
    pem_b64 = base64.encodebytes(der).decode()
    return ("-----BEGIN CERTIFICATE-----\n" +
            pem_b64 +
            "-----END CERTIFICATE-----\n").encode()


def pem_to_der(pem_path: str) -> bytes:
    raw = Path(pem_path).read_text()
    b64 = raw.replace("-----BEGIN CERTIFICATE-----", "") \
              .replace("-----END CERTIFICATE-----", "") \
              .replace("\n", "")
    return base64.b64decode(b64)


def compute_spki_pin(der_cert: bytes) -> str:
    """
    Compute the SHA-256 hash of the SubjectPublicKeyInfo (SPKI)
    block — this is exactly what OkHttp's CertificatePinner uses.
    Returns a string like: sha256/AbCd...==
    """
    if CRYPTOGRAPHY_AVAILABLE:
        cert = x509.load_der_x509_certificate(der_cert, default_backend())
        spki_der = cert.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo
        )
    else:
        # Fallback: use ssl module (less reliable SPKI extraction)
        # We need to strip the cert wrapper to get just SPKI
        # This is a simplified approach — use cryptography lib for accuracy
        spki_der = der_cert   # approximate
        print(f"{Y}[!] cryptography not installed — pin may be approximate{RST}")

    digest = hashlib.sha256(spki_der).digest()
    b64    = base64.b64encode(digest).decode()
    return f"sha256/{b64}"


def analyse_cert(der_cert: bytes) -> dict:
    """Return a dict with all relevant cert fields."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return {"error": "Install 'cryptography' for full analysis"}

    cert = x509.load_der_x509_certificate(der_cert, default_backend())

    # SAN entries
    try:
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san_ext.value.get_values_for_type(x509.DNSName)
        ip_addrs  = [str(ip) for ip in san_ext.value.get_values_for_type(x509.IPAddress)]
    except x509.ExtensionNotFound:
        dns_names = []
        ip_addrs  = []

    # Key info
    pub_key     = cert.public_key()
    key_size    = getattr(pub_key, "key_size", "N/A")

    return {
        "subject"    : cert.subject.rfc4514_string(),
        "issuer"     : cert.issuer.rfc4514_string(),
        "serial"     : hex(cert.serial_number),
        "not_before" : cert.not_valid_before_utc.isoformat(),
        "not_after"  : cert.not_valid_after_utc.isoformat(),
        "is_expired" : cert.not_valid_after_utc < datetime.datetime.now(datetime.timezone.utc),
        "algorithm"  : cert.signature_hash_algorithm.name,
        "key_size"   : key_size,
        "san_dns"    : dns_names,
        "san_ip"     : ip_addrs,
    }


def print_analysis(info: dict, pin: str, source: str) -> None:
    print(f"\n{BOLD}{B}══ Certificate Analysis ══════════════════════════════════{RST}")
    print(f"  Source    : {source}")
    print(f"  Subject   : {info.get('subject')}")
    print(f"  Issuer    : {info.get('issuer')}")
    print(f"  Serial    : {info.get('serial')}")
    print(f"  Not Before: {info.get('not_before')}")
    print(f"  Not After : {info.get('not_after')}",
          f"{R}[EXPIRED]{RST}" if info.get("is_expired") else f"{G}[VALID]{RST}")
    print(f"  Algorithm : {info.get('algorithm')}")
    print(f"  Key Size  : {info.get('key_size')} bits")
    print(f"  SAN DNS   : {', '.join(info.get('san_dns', []))}")
    print(f"  SAN IP    : {', '.join(info.get('san_ip', []))}")

    print(f"\n{BOLD}{Y}══ OkHttp Certificate Pin (computed) ════════════════════{RST}")
    print(f"\n  {G}{BOLD}{pin}{RST}\n")
    print(f"  Add to your CertificatePinner.Builder():")
    print(f'  {C}.add("10.0.2.2", "{pin}"){RST}')
    print()

    # Check against the hardcoded pin in MainActivity.kt
    known_pin = "sha256/+9PiUJGaE6FNwbbs1sy9nsEy5cn+yWpE+zDZJKBSUYw="
    if pin == known_pin:
        print(f"  {G}[✓] Pin MATCHES the pin hardcoded in MainActivity.kt{RST}")
    else:
        print(f"  {Y}[!] Pin differs from MainActivity.kt — different cert in use{RST}")
        print(f"  {Y}    App pin: {known_pin}{RST}")
        print(f"  {Y}    This:    {pin}{RST}")


def save_pem(der: bytes, out_path: str) -> None:
    Path(out_path).write_bytes(der_to_pem(der))
    print(f"{G}[+] Certificate saved as PEM → {out_path}{RST}")


def mitmproxy_ca_info(pem_path: str) -> None:
    """Show info about the mitmproxy CA cert (for device install instructions)."""
    print(f"\n{BOLD}{R}══ mitmproxy CA Certificate ══════════════════════════════{RST}")
    der = pem_to_der(pem_path)
    pin = compute_spki_pin(der)
    info = analyse_cert(der)
    print_analysis(info, pin, pem_path)
    print(f"""
{Y}To install this CA on Android emulator:{RST}
  1. adb push {pem_path} /sdcard/mitmproxy-ca.pem
  2. Settings → Security → Install from storage → pick mitmproxy-ca.pem
     (or use: adb shell am start -n com.android.certinstaller/.CertInstallerMain ...)
  3. Trust it as a "CA Certificate"
  4. Go to Settings → WiFi → Proxy → Manual → 127.0.0.1:8080
  
{R}Note: Android 7+ ignores user CAs for apps that set networkSecurityConfig.
Use Frida bypass script instead for those apps.{RST}
""")


# ── CLI ───────────────────────────────────────────────────────

def main():
    banner()
    parser = argparse.ArgumentParser(
        description="Extract and analyse TLS certificate pins"
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Server port (default: 5000)")
    parser.add_argument("--pem",  default=None,
                        help="Analyse a saved PEM file instead of live connection")
    parser.add_argument("--mitmproxy-ca", default=None,
                        help="Show info for mitmproxy CA cert")
    parser.add_argument("--save",  default=None,
                        help="Save extracted cert to PEM file")
    parser.add_argument("--json",  action="store_true",
                        help="Output JSON only")
    args = parser.parse_args()

    if args.mitmproxy_ca:
        mitmproxy_ca_info(args.mitmproxy_ca)
        return

    if args.pem:
        print(f"{Y}[*] Loading certificate from file: {args.pem}{RST}")
        der    = pem_to_der(args.pem)
        source = args.pem
    else:
        der    = extract_cert_from_server(args.host, args.port)
        source = f"live:{args.host}:{args.port}"

    pin  = compute_spki_pin(der)
    info = analyse_cert(der)

    if args.json:
        print(json.dumps({"pin": pin, **info}, indent=2, default=str))
        return

    print_analysis(info, pin, source)

    if args.save:
        save_pem(der, args.save)


if __name__ == "__main__":
    main()
