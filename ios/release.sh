#!/usr/bin/env bash
# Archive, sign and export Speedready for the App Store. Run it in Terminal on the Mac (the GUI session):
# code signing cannot reach the login keychain over SSH. Uploading the .ipa afterwards works over SSH.
#
#     ASC_KEY_PATH=…/AuthKey_XXXX.p8 ASC_KEY_ID=XXXX ASC_ISSUER=… ios/release.sh
#
# The App Store Connect API key lets Xcode register the bundle id and make the profiles itself
# (-allowProvisioningUpdates). The app record (io.github.cyoren.speedready) must exist in App Store Connect
# first; Apple's API cannot create it.
set -euo pipefail
cd "$(dirname "$0")"
: "${ASC_KEY_PATH:?}" "${ASC_KEY_ID:?}" "${ASC_ISSUER:?}"
AUTH=(-allowProvisioningUpdates -authenticationKeyPath "$ASC_KEY_PATH" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER")
rm -rf build
xcodebuild -project Speedready.xcodeproj -scheme Speedready -configuration Release \
  -destination 'generic/platform=iOS' -archivePath build/Speedready.xcarchive archive "${AUTH[@]}"
cat > build/ExportOptions.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyLists-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>teamID</key><string>2LPNFM9A89</string>
  <key>signingStyle</key><string>automatic</string>
</dict></plist>
EOF
xcodebuild -exportArchive -archivePath build/Speedready.xcarchive -exportOptionsPlist build/ExportOptions.plist \
  -exportPath build/ipa "${AUTH[@]}"
ls -la build/ipa/*.ipa
echo "upload: asc builds upload build/ipa/Speedready.ipa (or Transporter)"
