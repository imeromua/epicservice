package ua.epicservice.app

import android.os.Bundle
import com.getcapacitor.BridgeActivity

/**
 * MainActivity — головна активність EpicService Android-додатку.
 *
 * Розширює Capacitor BridgeActivity, яка завантажує веб-застосунок
 * (www/index.html) в нативний WebView з підтримкою Capacitor-плагінів.
 *
 * Усі основні функції (авторизація, пошук, офлайн-режим) реалізовані
 * в JavaScript-шарі (www/js/). Kotlin-код відповідає лише за нативні
 * можливості Android (камера, біометрія, статус-бар тощо).
 */
class MainActivity : BridgeActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        // Реєструємо плагіни перед викликом super.onCreate
        registerPlugin(EpicServicePlugin::class.java)
        super.onCreate(savedInstanceState)
    }
}
