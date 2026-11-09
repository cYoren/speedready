# Speedready for Android

The reader itself is not written twice. `app/build.gradle` adds `../web` to the asset
directories, so the APK ships the same HTML, JavaScript and dictionary that the website
serves, and `MainActivity` loads it from `file:///android_asset/index.html` inside a WebView.

That is the whole app. Its only permission is internet, used to download another language pair's
dictionary or a free book; the bundled pair, the books and everything a reader marks or learns stay
in the WebView's own storage on the device, and nothing about the reading is ever sent.

## Building

Needs JDK 17 or 21 (Gradle does not accept newer ones yet) and the Android SDK:

```
export JAVA_HOME=/path/to/jdk-21
echo "sdk.dir=$HOME/Android/sdk" > local.properties
./gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
```

Release builds are signed with this project's key (`tools/make_release_apk.sh`), whose SHA-256 is
`AllowedAPKSigningKeys` in `fdroid/io.github.cyoren.speedready.yml`; that is what lets F-Droid's
reproducible build verify the APK users download. The script refuses a tag that did not bump
`versionCode`, because the updater would ignore it.

## Layout

| path | what it is |
|---|---|
| `app/src/main/java/.../MainActivity.java` | the WebView host, ~120 lines |
| `app/src/main/AndroidManifest.xml` | one activity, internet only |
| `../web/` | the reader, shared with the website |
| `fastlane/metadata/` | the F-Droid listing |
