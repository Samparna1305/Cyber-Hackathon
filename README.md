#  J.A.R.V.I.S  
### Joint Attack Reconnaissance & Vulnerability Intelligence Squad

**Cyber Security Hackathon Project**  
**Domain 7 – Cryptography & Data Protection**  
**Problem Statement 31 – TLS Certificate Pinning Validation & Man-in-the-Middle Attack Demonstration**

---

##  Project Overview

This project demonstrates how secure mobile applications defend against **Man-in-the-Middle (MitM) attacks** performed through attacker-controlled interception environments.

The project focuses on:

- TLS communication validation
- HTTPS traffic interception attempts
- Certificate verification mechanisms
- Runtime security protections
- Mobile application defence strategies

The objective is to demonstrate how secure validation prevents interception even when network traffic is routed through an attacker proxy.

---

##  Problem Statement

Mobile applications exchange sensitive information through secure HTTPS communication.

Attackers may attempt to:

- Intercept traffic using MitM proxies
- Observe API requests and responses
- Present forged certificates
- Route traffic through attacker environments
- Perform runtime analysis

This project studies how TLS validation prevents such attacks.

---

##  Architecture Flow

```text
User
   │
   ▼
Android Application
   │
   ├── Root Detection
   ├── Emulator Detection
   ├── Frida Detection
   │
   ▼
TLS Validation Layer
(Certificate Verification)
   │
 ┌───────────────┬───────────────┐
 │               │
Valid Cert   Forged Certificate
 │               │
 ▼               ▼
Backend API  Attack Blocked
```

---

##  Attack Demonstration Flow

### Phase 1 – MitM Environment Setup

Traffic routing:

```text
Android Application
        │
        ▼
Burp Suite Proxy
(Attacker Environment)
        │
        ▼
Backend API
```

Evidence collected:

 Proxy configuration  
 Device routing  
 Burp setup  
 Application execution

---

### Phase 2 – TLS Validation

Application performs trust verification.

Observed flow:

```text
Burp Certificate
        │
        ▼
TLS Validation
        │
Certificate Rejected
        │
        ▼
Attack Blocked
```

Observed output:

```text
Trust anchor for certification path not found
```

Meaning:

- Certificate mismatch detected
- Connection rejected
- Interception prevented

---

##  Security Controls Implemented

### TLS Validation

Prevents acceptance of forged certificates.

### Root Detection

Detects modified environments used for privilege abuse.

### Emulator Detection

Identifies analysis environments.

### Frida Detection

Prevents runtime instrumentation attempts.

Implemented stack:

```text
TLS Validation
        +
Root Detection
        +
Emulator Detection
        +
Frida Detection
```

---

##  Cloud-Native Justification

The application follows a client-to-cloud communication model.

```text
Mobile Client
      │
HTTPS / TLS
      │
Cloud API Service
```

Security boundary:

**Client ↔ Cloud Communication Layer**

Primary focus:

- Secure transport
- TLS trust validation
- Interception resistance

---

##  MITRE ATT&CK Mapping

| Technique | MITRE ID | Mapping |
|-----------|----------|---------|
| Adversary-in-the-Middle | T1557 | Proxy interception attempt |
| Network Sniffing | T1040 | HTTPS traffic observation |
| Runtime Analysis Protection | Defensive | Root / Emulator / Frida checks |
| TLS Validation | Defensive | Certificate verification |

---

##  Evidence Available

### Environment Setup

 Android application running  

 Device connected  

 Burp Suite active  

---

### MitM Setup

 Proxy configuration  

 Traffic routing  

 Interception environment  

---

### Pinning Protection

 Certificate mismatch  

 Request rejection  

 TLS validation failure  

---

### Defence Layer

 Root detection  

 Emulator detection  

 Frida detection  

 Runtime validation  

---

##  Repository Structure

```text
Cyber-Hackathon
│
├── android_app
│
├── burp_configuration
│
├── tls_validation
│
├── runtime_security
│   ├── root_detection
│   ├── emulator_detection
│   └── frida_detection
│
├── screenshots
│
├── architecture
│
└── documentation
```

---

##  Running the Project

Verify device connection:

```bash
adb devices
```

Configure proxy:

```text
Host : Burp IP
Port : 8080
```

Launch application.

Route traffic.

Observe TLS validation.

Expected behaviour:

```text
Trust anchor for certification path not found
```

Result:

```text
MitM Attempt → Blocked
```

---

##  Current Implementation Status

| Component | Status |
|-----------|--------|
| Android Application |  Completed |
| Burp Setup |  Completed |
| Device Routing |  Completed |
| MitM Attempt |  Completed |
| TLS Validation |  Completed |
| Certificate Rejection |  Completed |
| Root Detection | Completed |
| Emulator Detection |  Completed |
| Frida Detection |  Completed |

---

## 🔮 Future Work

- Dynamic pinning bypass validation
- Runtime hook demonstrations
- Extended interception workflow
- Backup certificate pins
- Certificate rotation support
- Production deployment validation

---

##  Team J.A.R.V.I.S

**Team Number:** 18  

**Track:** Red Team (Offensive Security)

Members:

- Gangam Sai Samarth  
- Maytrai Sharma  
- S. Udhaya Sankari  
- Saswat Subhankar  
- Samparna Pattanaik  

**Internal Examiner:** Divya K V

---

##  Final Outcome

This project demonstrates that controlling the communication channel alone is insufficient to compromise secure mobile applications.

TLS validation and layered runtime protections successfully resisted interception attempts performed through an attacker-controlled environment.

**Attack Attempt → Validation → Rejection → Protection**
