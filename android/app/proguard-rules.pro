# R8 is enabled for release builds. The reader is JavaScript running in a WebView and it
# calls into this app through the JavaScript bridge, which R8 cannot see. Keep those
# methods, or the reader loses speech and file import in release builds only.
-keepattributes JavascriptInterface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# AndroidTTS is reached only through addJavascriptInterface() and reflection-free
# WebView dispatch, so keep the class name and its bridge members.
-keep class io.github.cyoren.speedready.AndroidTTS { *; }
