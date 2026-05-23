# CODE COMMENTS DOCUMENT
## J.A.R.V.I.S

--------------------------------------------------
1. PURPOSE
--------------------------------------------------

This document explains the major functional modules implemented in the project and the expected behaviour of each security component.

The implementation contains:

- TLS validation logic
- Runtime security checks
- HTTPS communication
- MitM validation environment
- Defensive verification

--------------------------------------------------
2. TLS VALIDATION MODULE
--------------------------------------------------

Module Purpose

Validate certificates received during HTTPS communication.

Responsibilities

1. Verify certificate authority

2. Validate hostname

3. Verify certificate chain

4. Reject forged certificates

Expected Flow

Server Certificate
        ↓
TLS Validation
        ↓
CA Check
Hostname Check
Chain Validation
        ↓
PASS / FAIL

Observed Result

Trust anchor for certification path not found

Meaning

Certificate rejected

MitM blocked

--------------------------------------------------
3. ROOT DETECTION MODULE
--------------------------------------------------

Purpose

Detect privileged environments.

Checks Performed

- Root binaries
- Elevated permissions
- Modified environment

Expected Output

PASS

or

WARNING

Risk Mitigated

Privilege escalation

--------------------------------------------------
4. EMULATOR DETECTION MODULE
--------------------------------------------------

Purpose

Detect virtual execution environments.

Checks

- Emulator signatures
- Virtual hardware
- Device properties

Expected Output

PASS

Risk Mitigated

Sandbox analysis

--------------------------------------------------
5. FRIDA DETECTION MODULE
--------------------------------------------------

Purpose

Detect runtime instrumentation.

Checks

- Hook indicators
- Runtime traces
- Instrumentation signatures

Expected Output

PASS

Risk Mitigated

Runtime manipulation

--------------------------------------------------
6. ATTACK MODULE
--------------------------------------------------

Tool Used

Burp Suite

Purpose

Traffic interception simulation

Flow

Android App
      ↓
Burp Proxy
      ↓
Backend

Expected Behaviour

Burp certificate presented

TLS validation triggered

Connection rejected

--------------------------------------------------
7. RESULT
--------------------------------------------------

Attack Attempt
        ↓
TLS Validation
        ↓
Certificate Rejected
        ↓
MitM Blocked
