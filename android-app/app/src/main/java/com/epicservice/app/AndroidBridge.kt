package com.epicservice.app

import android.webkit.JavascriptInterface
import android.widget.Toast

/**
 * JavaScript-міст між WebView та нативним Android кодом.
 * Дозволяє веб-додатку викликати нативні функції:
 * - Біометрична автентифікація
 * - Вібрація (haptic feedback)
 * - Нативні сповіщення
 * - Перевірка стану з'єднання
 */
class AndroidBridge(private val activity: MainActivity) {

    @JavascriptInterface
    fun isBiometricAvailable(): Boolean {
        return activity.isBiometricAvailable()
    }

    @JavascriptInterface
    fun requestBiometric() {
        activity.runOnUiThread {
            activity.performBiometricAuth { success ->
                val js = if (success) {
                    "StandaloneAuth.onBiometricSuccess()"
                } else {
                    "StandaloneAuth.onBiometricFailure()"
                }
                activity.runOnUiThread {
                    val webView = activity.findViewById<android.webkit.WebView>(R.id.webView)
                    webView.evaluateJavascript(js, null)
                }
            }
        }
    }

    @JavascriptInterface
    fun vibrate(milliseconds: Long) {
        @Suppress("DEPRECATION")
        val vibrator = activity.getSystemService(android.content.Context.VIBRATOR_SERVICE)
                as? android.os.Vibrator
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            vibrator?.vibrate(
                android.os.VibrationEffect.createOneShot(
                    milliseconds,
                    android.os.VibrationEffect.DEFAULT_AMPLITUDE
                )
            )
        } else {
            @Suppress("DEPRECATION")
            vibrator?.vibrate(milliseconds)
        }
    }

    @JavascriptInterface
    fun showToast(message: String) {
        activity.runOnUiThread {
            Toast.makeText(activity, message, Toast.LENGTH_SHORT).show()
        }
    }

    @JavascriptInterface
    fun isOnline(): Boolean {
        val connectivityManager = activity.getSystemService(
            android.content.Context.CONNECTIVITY_SERVICE
        ) as? android.net.ConnectivityManager
        val network = connectivityManager?.activeNetwork
        val capabilities = connectivityManager?.getNetworkCapabilities(network)
        return capabilities?.hasCapability(
            android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET
        ) == true
    }

    @JavascriptInterface
    fun getAppVersion(): String {
        return try {
            val packageInfo = activity.packageManager.getPackageInfo(activity.packageName, 0)
            packageInfo.versionName ?: "1.0.0"
        } catch (e: Exception) {
            "1.0.0"
        }
    }
}
