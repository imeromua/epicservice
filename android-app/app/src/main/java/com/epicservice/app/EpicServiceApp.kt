package com.epicservice.app

import android.app.Application

/**
 * Головний клас додатку EpicService.
 */
class EpicServiceApp : Application() {

    companion object {
        lateinit var instance: EpicServiceApp
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }
}
