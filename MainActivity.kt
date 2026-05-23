package com.example.secureapp

import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.util.Log
import android.widget.TextView
import android.widget.Button
import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import android.os.Build
import java.io.BufferedReader
import java.io.InputStreamReader
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var logTextView: TextView
    private lateinit var testButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        logTextView = findViewById(R.id.logTextView)
        testButton = findViewById(R.id.testButton)

        // Perform initial security checks
        runSecurityChecks()

        testButton.setOnClickListener {
            logTextView.text = "Initiating connection to secure backend...\n"
            executeSecureRequest()
        }
    }

    private fun runSecurityChecks() {
        val rootStatus = isDeviceRooted()
        val emulatorStatus = isEmulator()
        val fridaStatus = detectFrida()

        val securityReport = StringBuilder()
        securityReport.append("=== SECURITY CHECKS ===\n")
        securityReport.append("Device Rooted: ${if (rootStatus) "WARNING" else "PASS"}\n")
        securityReport.append("Emulator Environment: ${if (emulatorStatus) "DETECTED" else "PASS"}\n")
        securityReport.append("Frida Hooking Detected: ${if (fridaStatus) "CRITICAL" else "PASS"}\n")
        securityReport.append("=======================\n\n")

        Log.d("SECURITY_CHECK", securityReport.toString())
        runOnUiThread {
            logTextView.append(securityReport.toString())
        }

        if (fridaStatus) {
            logTextView.append("CRITICAL: Instrumentation framework detected. Exiting app or disabling sensitive operations!\n")
            // In a production defensive app, you would terminate or enter self-destruction state:
            // finish()
        }
    }

    private fun executeSecureRequest() {
        // OkHttp Certificate Pinning setup
        // Define the target domain and the base64-encoded SHA-256 fingerprint of the public key
        val certificatePinner = CertificatePinner.Builder()
            .add(
                "10.0.2.2", // Android emulator host loopback address
                "sha256/+9PiUJGaE6FNwbbs1sy9nsEy5cn+yWpE+zDZJKBSUYw=" // Generated certificate pin
            )
            .add(
                "10.0.2.2",
                "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=" // Backup Pin example for key rotation
            )
            .build()

        val client = OkHttpClient.Builder()
            .certificatePinner(certificatePinner)
            .build()

        thread {
            try {
                val request = Request.Builder()
                    .url("https://10.0.2.2:5000/login")
                    .build()

                val response = client.newCall(request).execute()
                val responseBody = response.body?.string() ?: "Empty body"

                runOnUiThread {
                    logTextView.append("Success: Connection established!\n")
                    logTextView.append("Response from server:\n$responseBody\n")
                }
                Log.d("API_RESPONSE", responseBody)

            } catch (e: Exception) {
                runOnUiThread {
                    logTextView.append("\nConnection Error / Verification Failed:\n")
                    logTextView.append("${e.message}\n")
                }
                Log.e("ERROR", "TLS Connection failed verification check", e)
            }
        }
    }

    /**
     * Defensive Check 1: Root Detection
     * Inspects system directories for the 'su' executable.
     */
    private fun isDeviceRooted(): Boolean {
        val paths = arrayOf(
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/system/bin/failsafe/su",
            "/data/local/su"
        )
        for (path in paths) {
            if (File(path).exists()) return true
        }
        return false
    }

    /**
     * Defensive Check 2: Emulator Detection
     * Inspects Build fields to detect execution in standard emulators.
     */
    private fun isEmulator(): Boolean {
        return (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic"))
                || Build.FINGERPRINT.startsWith("generic")
                || Build.FINGERPRINT.startsWith("unknown")
                || Build.HARDWARE.contains("goldfish")
                || Build.HARDWARE.contains("ranchu")
                || Build.MODEL.contains("google_sdk")
                || Build.MODEL.contains("Emulator")
                || Build.MODEL.contains("Android SDK built for x86")
                || Build.MANUFACTURER.contains("Genymotion")
                || Build.PRODUCT.contains("sdk_google")
                || Build.PRODUCT.contains("google_sdk")
                || Build.PRODUCT.contains("sdk")
                || Build.PRODUCT.contains("sdk_x86")
                || Build.PRODUCT.contains("vbox86p")
                || Build.PRODUCT.contains("emulator")
                || Build.PRODUCT.contains("simulator")
    }

    /**
     * Defensive Check 3: Frida Hooking Detection
     * Inspects maps memory layout to check if frida-agent is injected into current process memory.
     */
    private fun detectFrida(): Boolean {
        try {
            val file = File("/proc/self/maps")
            if (file.exists()) {
                val reader = BufferedReader(InputStreamReader(file.inputStream()))
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    if (line?.contains("frida", ignoreCase = true) == true) {
                        reader.close()
                        return true
                    }
                }
                reader.close()
            }
        } catch (e: Exception) {
            // Ignore permissions or file read exceptions
        }
        return false
    }
}
