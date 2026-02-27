package ua.epicservice.app

import android.content.Context
import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/**
 * EpicServicePlugin — Capacitor-плагін для нативних функцій Android.
 *
 * Надає JavaScript-коду доступ до:
 *   - Біометричної автентифікації (відбиток пальця / обличчя)
 *   - Системної інформації пристрою
 *   - Вібрації
 */
@CapacitorPlugin(name = "EpicService")
class EpicServicePlugin : Plugin() {

    /**
     * Перевіряє наявність біометрії та запускає підтвердження.
     * Викликається з JS: Capacitor.Plugins.EpicService.biometricAuth()
     */
    @PluginMethod
    fun biometricAuth(call: PluginCall) {
        val activity = activity as? FragmentActivity
            ?: run { call.reject("Activity не знайдено"); return }

        val biometricManager = BiometricManager.from(context)
        val canAuthenticate = biometricManager.canAuthenticate(BIOMETRIC_STRONG or DEVICE_CREDENTIAL)

        if (canAuthenticate != BiometricManager.BIOMETRIC_SUCCESS) {
            val reason = when (canAuthenticate) {
                BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> "Пристрій не підтримує біометрію"
                BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> "Біометричне обладнання недоступне"
                BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> "Біометрія не налаштована"
                else -> "Біометрія недоступна"
            }
            call.reject(reason)
            return
        }

        val executor = ContextCompat.getMainExecutor(context)
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                val ret = JSObject().put("success", true)
                call.resolve(ret)
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                if (errorCode == BiometricPrompt.ERROR_USER_CANCELED ||
                    errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON
                ) {
                    call.reject("Скасовано користувачем")
                } else {
                    call.reject("Помилка біометрії: $errString")
                }
            }

            override fun onAuthenticationFailed() {
                // Відбиток не розпізнано — не відхиляємо call, даємо користувачу ще спробу
            }
        }

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("EpicService")
            .setSubtitle("Підтвердіть особу для входу")
            .setAllowedAuthenticators(BIOMETRIC_STRONG or DEVICE_CREDENTIAL)
            .build()

        activity.runOnUiThread {
            BiometricPrompt(activity, executor, callback).authenticate(promptInfo)
        }
    }

    /**
     * Повертає базову інформацію про пристрій.
     */
    @PluginMethod
    fun getDeviceInfo(call: PluginCall) {
        val info = JSObject()
            .put("manufacturer", Build.MANUFACTURER)
            .put("model", Build.MODEL)
            .put("sdkVersion", Build.VERSION.SDK_INT)
            .put("release", Build.VERSION.RELEASE)
        call.resolve(info)
    }

    /**
     * Вібрує пристрій.
     */
    @PluginMethod
    fun vibrate(call: PluginCall) {
        val duration = call.getLong("duration", 50L) ?: 50L
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE)
                    as? android.os.VibratorManager
                vibratorManager?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as? android.os.Vibrator
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(android.os.VibrationEffect.createOneShot(duration, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(duration)
            }
            call.resolve()
        } catch (e: Exception) {
            call.reject("Помилка вібрації: ${e.message}")
        }
    }
}
