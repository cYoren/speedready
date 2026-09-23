#!/usr/bin/env bash
# Build and sign the release APK for F-Droid reproducible builds, and print the fingerprint
# the metadata needs.
#
#     tools/make_release_apk.sh
#
# First run creates android/speedready.keystore and android/keystore.properties.
#
#   *** BACK THE KEYSTORE UP, IN MORE THAN ONE PLACE, AND KEEP THE PASSWORD. ***
#   F-Droid ties the app to this key. If you lose it, this app can never be updated again:
#   not by you, not by F-Droid. There is no recovery and no reset.
#
# Both files are gitignored. Nothing here is committed.
set -euo pipefail

cd "$(dirname "$0")/.."
AND=android
STORE="$AND/speedready.keystore"
PROPS="$AND/keystore.properties"
ALIAS=speedready

for c in keytool apksigner; do
  command -v "$c" >/dev/null || { echo "need $c (JDK / Android build-tools) on PATH" >&2; exit 1; }
done

if [ ! -f "$STORE" ]; then
  echo "No keystore yet. Creating $STORE"
  echo "Choose a password you will not lose. Nothing can recover this key."
  read -rsp "password: " PW; echo
  read -rsp "again:    " PW2; echo
  [ "$PW" = "$PW2" ] || { echo "passwords differ" >&2; exit 1; }
  [ ${#PW} -ge 8 ] || { echo "keytool requires at least 8 characters" >&2; exit 1; }
  keytool -genkeypair -v -keystore "$STORE" -alias "$ALIAS" \
    -keyalg RSA -keysize 4096 -validity 10000 \
    -storepass "$PW" -keypass "$PW" \
    -dname "CN=cYoren, OU=Speedready, O=Speedready, C=BR"
  umask 077
  cat > "$PROPS" <<EOF
storeFile=$(basename "$STORE")
storePassword=$PW
keyAlias=$ALIAS
keyPassword=$PW
EOF
  chmod 600 "$PROPS" "$STORE"
  echo "Created $STORE and $PROPS (both gitignored). Back them up now."
fi

echo "Building release APK"
(cd "$AND" && ./gradlew --quiet clean :app:assembleRelease)

APK=$(find "$AND/app/build/outputs/apk/release" -name '*.apk' | head -1)
[ -n "$APK" ] || { echo "no APK produced" >&2; exit 1; }

VER=$(sed -n "s/.*versionName '\(.*\)'.*/\1/p" "$AND/app/build.gradle")
OUT="$AND/app/build/outputs/apk/release/speedready-$VER.apk"
[ "$APK" = "$OUT" ] || cp "$APK" "$OUT"

echo
apksigner verify --print-certs "$OUT" | sed -n 's/.*SHA-256 digest: *//p' | head -1 | tr -d ' \n' > /tmp/speedready-fp.txt
FP=$(cat /tmp/speedready-fp.txt)
echo "APK:         $OUT"
echo "versionName: $VER"
echo "SHA-256:     $FP"
echo
echo "Next:"
echo "  1. gh release create v$VER --repo cYoren/speedready --title v$VER --notes-file fastlane/metadata/android/en-US/changelogs/2.txt '$OUT'"
echo "  2. put this in android/fdroid/io.github.cyoren.speedready.yml:"
echo "       AllowedAPKSigningKeys: $FP"
