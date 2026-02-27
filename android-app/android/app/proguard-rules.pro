# Capacitor
-keep class com.getcapacitor.** { *; }
-keep @com.getcapacitor.annotation.CapacitorPlugin class * { *; }

# EpicService Plugin
-keep class ua.epicservice.app.EpicServicePlugin { *; }

# Androidx
-keep class androidx.** { *; }
-dontwarn androidx.**

# Kotlin
-keep class kotlin.** { *; }
-dontwarn kotlin.**

# OkHttp (if used)
-dontwarn okhttp3.**
-dontwarn okio.**
