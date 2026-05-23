# THREAT MODEL WRITE-UP
## J.A.R.V.I.S

--------------------------------------------------
1. SYSTEM OVERVIEW
--------------------------------------------------

The system demonstrates TLS validation against controlled Man-in-the-Middle attacks.

Architecture Layers

Client Layer

Android Application

Transport Layer

TLS / HTTPS

Attacker Layer

Burp Proxy

Backend Layer

Cloud API

Security Boundary

Client ↔ Cloud Communication

--------------------------------------------------
2. ASSETS
--------------------------------------------------

Protected Assets

- HTTPS requests
- HTTPS responses
- Authentication tokens
- API communication
- Session identifiers
- User information

Secondary Assets

- Runtime integrity
- Certificate trust chain
- Validation logic

--------------------------------------------------
3. ADVERSARY PROFILE
--------------------------------------------------

Adversary Type

Network-positioned attacker

Capabilities

Traffic interception

Proxy routing

Certificate presentation

HTTPS observation

Tool

Burp Suite

Goal

Observe traffic

Modify communication

Bypass validation

--------------------------------------------------
4. ATTACK SURFACE
--------------------------------------------------

Primary Surface

Client ↔ Cloud TLS channel

Secondary Surfaces

Runtime Layer

Trust Store

Proxy Configuration

Backend API

Root Environment

Emulator Environment

--------------------------------------------------
5. ATTACK VECTOR
--------------------------------------------------

Implemented Vector

Proxy-based MitM

Flow

Device
   ↓
Burp Routing
   ↓
Certificate Injection
   ↓
TLS Validation
   ↓
Blocked

Future Vectors

Runtime hook injection

Frida bypass

Trust manipulation

Certificate replacement

--------------------------------------------------
6. LAYER OF INTERVENTION
--------------------------------------------------

Network Layer

Role

Traffic interception

Tools

Burp

Wireshark

mitmproxy


Host Layer

Role

Runtime execution

Tools

Android Device


Application Layer

Role

TLS validation

Components

Certificate verification


Transport Layer

Role

HTTPS protection

Component

TLS

Primary Layer

Application + Transport

Supporting Layer

Network + Host

--------------------------------------------------
7. MITRE ATT&CK
--------------------------------------------------

Technique

Adversary-in-the-Middle

ID

T1557

Evidence

Proxy configuration


Technique

Network Sniffing

ID

T1040

Evidence

TLS observation


Technique

Runtime Protection

Type

Defensive

Evidence

Root

Emulator

Frida checks


Technique

Certificate Validation

Type

Defensive

Evidence

Trust anchor failure

--------------------------------------------------
8. LIMITATIONS
--------------------------------------------------

Current Scope

MitM attempt

TLS rejection

Runtime protection

Pending Scope

Dynamic bypass

Successful interception

Backup pins

Certificate rotation

--------------------------------------------------
9. DEFENSIVE CONTROLS
--------------------------------------------------

TLS Validation

Reject forged certificates

Root Detection

Prevent privilege abuse

Emulator Detection

Prevent analysis

Frida Detection

Prevent runtime instrumentation

--------------------------------------------------
10. FINAL STATUS
--------------------------------------------------

MitM Attempt

Completed

TLS Validation

Completed

Certificate Rejection

Completed

Runtime Security

Completed

Dynamic Bypass

Pending

Overall Result

Attack prevented
