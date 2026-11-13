Paste this over the description of https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884
(Edit -> replace the body -> Save). Every line below is already true of the branch and the tagged
release; there are no TODO lines left. Version numbers are deliberately not repeated here: the build
entry is whatever `metadata/io.github.cyoren.speedready.yml` in the merge request names, so update
that file to the newest tag instead of editing this text.

---

## Checklist

### Policy

* [x] The app complies with the [inclusion criteria](https://f-droid.org/docs/Inclusion_Policy).
* [x] The original app author has been notified (and does not oppose the inclusion). If you are not the author, please paste the link of the reply from the author.
  <br>I am the author.
* [x] The upstream app source code repo contains the app metadata in a [Fastlane](https://gitlab.com/snippets/1895688) or [Triple-T](https://gitlab.com/snippets/1901490) folder structure. The summary and description must be included and images, icon, and changelog should also be provided for better user experience. The `en-US` locale must be included.
  <br>`fastlane/metadata/android/en-US/` with title, short and full description, icon, three phone screenshots and a changelog for versionCode 1 through 9.

### Docs

* [x] Please read [the guide](https://gitlab.com/fdroid/fdroiddata/-/blob/master/CONTRIBUTING.md) first if this is your first contribution.
* [x] Please make sure your metadata follows the best practice in [our templates](https://gitlab.com/fdroid/fdroiddata/tree/master/templates).
* [x] Please read the [Build Metadata Reference](https://f-droid.org/docs/Build_Metadata_Reference/) and make sure your metadata is valid.
* [x] Please read the [Quick Start Guide](https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide/).

### Merge Request Setup

* [x] The title of this merge request should follow "New app: app name" format.
* [x] Please make sure your fdroiddata fork is public and your branch is not protected. See <https://docs.gitlab.com/user/project/repository/branches/protected/>.
* [x] Please read [our Git guide](https://gitlab.com/fdroid/wiki/-/wikis/Tips-for-fdroiddata-contributors/Git-Usage) if you don't know how to rebase your branch. Don't rebase your branch if there is no conflict.
* [x] All related [fdroiddata](https://gitlab.com/fdroid/fdroiddata/issues) and [RFP issues](https://gitlab.com/fdroid/rfp/issues) have been referenced in this merge request
  <br>There is no RFP issue for this app; it is submitted directly by its author.
* [x] Please only submit one app in one MR.

### Metadata

* [x] Metadata must be put in `metadata/<applicationId>.yml`.
  <br>`metadata/io.github.cyoren.speedready.yml`
* [x] Metadata must be a valid YAML file.
* [x] Metadata must use LF as line ending.
* [x] Don't add summary/description/changelog/images or anything that should be provided in upstream repo. Please check the Changes tab to make sure there is no other unrelated files added in the MR.
  <br>Removed: `Summary`, `Description` and `AutoName` are gone. The MR changes exactly one file, and it now contains only what fdroiddata needs.
* [x] Releases are tagged and auto update is enabled unless there is a special reason.
  <br>`AutoUpdateMode: Version`, `UpdateCheckMode: Tags`.
* [x] There is an issue tracker and contact info of the author so that we can report bugs and contact the author.
* [x] An AuthorName must be added. It doesn't need to be the real name.
* [x] External repos are added as git submodules instead of srclibs. You can update git submodules without opening an MR in this repo and the submodule is covered by our scanner.
  <br>No external repos. The app has one Maven dependency, `androidx.core:core` (used for the
  edge-to-edge window insets Android 15+ requires); everything else is the WebView host in
  `android/app/src/main/java` plus the reader in `web/`.
* [x] Enable [Reproducible Builds](https://f-droid.org/docs/Reproducible_Builds). We'll use your signature for improved security/reliability, also allowing users to switch between different channels. Do note that if you don't enable reproducible build then the apk will be signed with our key so you can't enable it later. If you can't enable this, please add the reasons here.
  <br>Enabled. `Binaries` and `AllowedAPKSigningKeys` are set, and the APK for this build entry is published under the release tag.
  <br>The app is a WebView wrapper whose payload is static assets, and `dependenciesInfo` is
  disabled, so the build is deterministic. Re-measured on the commit this build entry names
  (JDK 21, Gradle 8.11.1 as pinned in the wrapper, `minifyEnabled`/`shrinkResources` on):
  <br>- two clean signed builds are byte-identical: `sha256 d468c5c8e512170c7f2310fad7c9a66f0bf2abd9b8070d33727c4ba4f530ea50`
  <br>- a clean build without signing credentials produces the same 68 zip entries, byte-for-byte, as the signed APK
  <br>- clean unsigned APK: `sha256 f11db85db7cb99a3b96568ef48303e202c757bde3a6a5ed0db19618a9ecd1cb8`
  <br>The signing config only applies when a local `keystore.properties` is present, so the F-Droid
  builder without one produces an unsigned APK with identical payload bytes. The APK for the build
  entry in this merge request is published under `Binaries` and signed with the key in
  `AllowedAPKSigningKeys`.
* [x] Setup abi split if the APK is large and the splitted ones can be much smaller.
  <br>Not applicable: no native code, single ABI-independent APK.
* [x] Only the latest versions should be kept in the metadata before it's merged. If you update the metadata, please replace the old versions with the new ones.
  <br>One build entry, naming the newest release tag with its versionName, versionCode and full commit hash.
* [x] Don't add any disabled versions in the metadata.
* [x] The `commit` field should be the full hash. Please don't use tag or branch in commit.
  <br>`commit:` is the full 40-character hash the build entry checks out, never a tag or a branch.

### Pipeline

* [x] All pipelines should pass.
  <br>The last MR pipeline (`2886187302`) passed all nine jobs, including F-Droid lint, checkupdates and build. Rerun it after the build entry is bumped to the current tag; checkupdates reports the version it will build.
* [x] All warnings and errors in the Reports tab should be fixed or explained.
  <br>The pipeline's test report contains zero tests and no test failures; no code-quality report was generated. All lint and build jobs passed.
* [x] F-Droid CI runners are under GitLab's FOSS program, so there's no need for you to pay for any CI time. If Gitlab starts asking for phone numbers or credit cards don't submit anything, just leave a note in the MR so we know we need to trigger the CI.

---

Thanks for the review @seekme-seekyou. All four points are addressed:

1. Template followed above, with Reproducible Builds enabled.
2. `Binaries` and `AllowedAPKSigningKeys` added.
3. `Summary`, `Description` and `AutoName` removed from the yaml; they live in the upstream Fastlane folder.
4. `commit` is now the full hash.

Since the previous update the app has released several versions. That release removed the non-commercial MUSE data from the dictionary pipeline and corrected the listing to describe the shipped German-to-Portuguese dictionary only; the commit also removed the workstation-specific Android SDK path, so the build uses `ANDROID_HOME` and works from `android/app` with no local SDK or signing properties. The build entry attached here is the current tag.

The release the build entry now names brings the reading work: the reader accepts any language pair, imports PDFs, downloads free books from the Project Gutenberg catalogue without leaving the app, and the desktop app and the website now choose the same translation for a word (99.3% agreement over the starter book, up from 94.4%). Noun genders are in nine languages. `versionName`/`versionCode` live in `android/app/build.gradle`, the signing key is unchanged from the previous build entry, and the APK published under `Binaries` for this tag verifies against `AllowedAPKSigningKeys`.
