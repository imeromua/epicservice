# EpicService ProGuard Rules

# Keep WebView JavaScript interface
-keepclassmembers class com.epicservice.app.AndroidBridge {
    public *;
}

# Keep biometric classes
-keep class androidx.biometric.** { *; }

# Keep data classes
-keep class com.epicservice.app.data.** { *; }
