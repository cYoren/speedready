# Speedready for Android

The reader itself is not written twice. `app/build.gradle` adds `../web` to the asset
directories, so the APK ships the same HTML, JavaScript and dictionary that the website
serves, and `MainActivity` loads it from `file:///android_asset/index.html` inside a WebView.

That is the whole app. It declares **no permissions**, opens no network connections, and
keeps everything a reader marks or learns in the WebView's own storage on the device.

## Building

Needs JDK 17 or 21 (Gradle does not accept newer ones yet) and the Android SDK:

```
export JAVA_HOME=/path/to/jdk-21
echo "sdk.dir=$HOME/Android/sdk" > local.properties
./gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
```

Release builds are unsigned on purpose: F-Droid builds this source itself and signs the
result with its own key.

## Layout

| path | what it is |
|---|---|
| `app/src/main/java/.../MainActivity.java` | the WebView host, ~120 lines |
| `app/src/main/AndroidManifest.xml` | one activity, no permissions |
| `../web/` | the reader, shared with the website |
| `fastlane/metadata/` | the F-Droid listing |
