# SETUP DOCUMENTATION
## J.A.R.V.I.S
Joint Attack Reconnaissance & Vulnerability Intelligence Squad

Domain:
Cryptography & Data Protection

Problem Statement:
TLS Certificate Pinning Validation & Man-in-the-Middle Attack Demonstration

--------------------------------------------------
1. PURPOSE
--------------------------------------------------

This document explains the environment preparation and execution steps required for reproducing the TLS interception demonstration.

The setup supports:

- Android application deployment
- Burp proxy routing
- TLS validation observation
- Runtime security checks
- Controlled MitM simulation

--------------------------------------------------
2. SYSTEM REQUIREMENTS
--------------------------------------------------

Hardware Requirements

Client Device

- Android Phone
OR
- Android Emulator

Host Machine

- Windows Laptop
- Minimum 8GB RAM
- WiFi connectivity

--------------------------------------------------
3. SOFTWARE REQUIREMENTS
--------------------------------------------------

Required Tools

1. Android Platform Tools

Purpose:
Device connection and application installation

Commands:

adb devices

adb install app-debug.apk

adb logcat


2. Burp Suite Community Edition

Purpose:

- HTTPS interception
- Proxy configuration
- Traffic observation
- MitM simulation


3. Android Application

Components:

- TLS validation layer
- Root detection
- Emulator detection
- Frida detection


Optional Tools

- Wireshark
- mitmproxy
- Frida

(Current implementation uses Burp environment)

--------------------------------------------------
4. ENVIRONMENT ARCHITECTURE
--------------------------------------------------

Android App
      │
      ▼
Runtime Security Layer

Root Detection
Emulator Detection
Frida Detection

      │
      ▼
TLS Validation Layer

CA Verification
Hostname Verification
Certificate Chain Validation

      │
      ▼
HTTPS Channel

      │
      ▼
Cloud Backend

Attack Path

Android App
      │
Traffic Routed
      │
      ▼
Burp Proxy
      │
Forged Certificate
      │
      ▼
TLS Validation
      │
      ▼
Connection Rejected

--------------------------------------------------
5. DEVICE SETUP
--------------------------------------------------

Step 1

Enable developer mode

Settings

About Device

Version

Tap Build Number

Enable:

USB Debugging


Step 2

Connect device

Run:

adb devices

Expected:

List of devices attached

device_id    device



--------------------------------------------------
6. APPLICATION DEPLOYMENT
--------------------------------------------------

Install application

Command:

adb install -r app-debug.apk

Expected:

Success

Verify:

Application visible inside device



--------------------------------------------------
7. BURP CONFIGURATION
--------------------------------------------------

Launch Burp Suite

Select:

Temporary Project

Use Default Settings


Proxy Listener

Host:

All Interfaces

Port:

8080




--------------------------------------------------
8. TRAFFIC ROUTING
--------------------------------------------------

Configure phone proxy

WiFi Settings

Manual Proxy

Host:

Laptop IP

Port:

8080


Flow:

App
 ↓
Burp
 ↓
Backend



--------------------------------------------------
9. MITM VALIDATION
--------------------------------------------------

Open application

Trigger secure HTTPS request

Observed sequence:

Traffic Routed
        ↓
Burp Interception
        ↓
Certificate Presented
        ↓
TLS Validation
        ↓
Trust Failure

Observed output:

Trust anchor for certification path not found

Meaning:

Certificate mismatch detected

Request rejected

MitM blocked



--------------------------------------------------
10. RUNTIME SECURITY
--------------------------------------------------

Root Detection

Purpose:

Prevent privilege escalation

Evidence:

[INSERT ROOT CHECK]


Emulator Detection

Purpose:

Prevent analysis environments




Frida Detection

Purpose:

Detect instrumentation





--------------------------------------------------
11. CURRENT STATUS
--------------------------------------------------

Completed

      Android App
      
      Burp Setup
      
      Routing
      
      MitM Attempt
      
      TLS Validation
      
      Root Detection
      
      Emulator Detection
      
      Frida Detection


Future Work

      Dynamic bypass
      
      Successful interception
      
      Backup pins
