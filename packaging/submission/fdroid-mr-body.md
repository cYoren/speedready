Paste this over the description of https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884
(Edit -> replace the body -> Save). Every line below is already true of the branch and the tagged
release; there are no TODO lines left.

---

## Checklist

### Policy

* [x] The app complies with the [inclusion criteria](https://f-droid.org/docs/Inclusion_Policy).
* [x] The original app author has been notified (and does not oppose the inclusion). If you are not the author, please paste the link of the reply from the author.
  <br>I am the author.
* [x] The upstream app source code repo contains the app metadata in a [Fastlane](https://gitlab.com/snippets/1895688) or [Triple-T](https://gitlab.com/snippets/1901490) folder structure. The summary and description must be included and images, icon, and changelog should also be provided for better user experience. The `en-US` locale must be included.
  <br>`fastlane/metadata/android/en-US/` with title, short and full description, icon, three phone screenshots and changelogs for versionCode 1, 2, 3 and 4.

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
  <br>No external repos: the app has no dependencies at all (`dependencies { }`).
* [x] Enable [Reproducible Builds](https://f-droid.org/docs/Reproducible_Builds). We'll use your signature for improved security/reliability, also allowing users to switch between different channels. Do note that if you don't enable reproducible build then the apk will be signed with our key so you can't enable it later. If you can't enable this, please add the reasons here.
  <br>Enabled. `Binaries` and `AllowedAPKSigningKeys` are set, and `speedready-v1.0.4.apk` is published.
  <br>The app is a WebView wrapper with no dependencies, `minifyEnabled false`, and `dependenciesInfo`
  disabled, so the build is deterministic. Measured on commit `d1fe0b3` (tag `v1.0.4`, JDK 21,
  Gradle 8.11.1 as pinned in the wrapper):
  <br>- two clean signed builds are byte-identical: `sha256 554c6a448fb6bc421f36b8428d8572e15d55154179527e52f8073f7e3f6588fe`
  <br>- a clean unsigned build without signing credentials has the same 21 non-signature zip entries, byte-for-byte, as the signed APK
  <br>- clean unsigned APK: `sha256 80180a8999dfd608ef0eed3f6363facdc3fdab29721ab90de0fb25b5dd42ac66`
  <br>The signing config only applies when a local `keystore.properties` is present, so the F-Droid
  builder without one produces an unsigned APK with identical payload bytes.
* [x] Setup abi split if the APK is large and the splitted ones can be much smaller.
  <br>Not applicable: no native code, single ABI-independent APK.
* [x] Only the latest versions should be kept in the metadata before it's merged. If you update the metadata, please replace the old versions with the new ones.
  <br>One build entry, versionCode 4.
* [x] Don't add any disabled versions in the metadata.
* [x] The `commit` field should be the full hash. Please don't use tag or branch in commit.
  <br>`commit: d1fe0b38263d461267453e7275c0a2f2c2971027` (full hash for `v1.0.4`).

### Pipeline

* [ ] All pipelines should pass.
  <br>Latest run for the existing MR head `510dcf4f` failed immediately with zero jobs, before any build or test ran. A maintainer must retrigger after the GitLab account-verification gate is cleared; there is no build result to assess yet.
* [ ] All warnings and errors in the Reports tab should be fixed or explained.
  <br>Same status: no jobs have run, so there is nothing reported yet.
* [x] F-Droid CI runners are under GitLab's FOSS program, so there's no need for you to pay for any CI time. If Gitlab starts asking for phone numbers or credit cards don't submit anything, just leave a note in the MR so we know we need to trigger the CI.

---

Thanks for the review @seekme-seekyou. All four points are addressed:

1. Template followed above, with Reproducible Builds enabled.
2. `Binaries` and `AllowedAPKSigningKeys` added.
3. `Summary`, `Description` and `AutoName` removed from the yaml; they live in the upstream Fastlane folder.
4. `commit` is now the full hash.

Since the previous update, the app has released `v1.0.4` (`versionCode 4`). This release removes the non-commercial MUSE data from the dictionary pipeline and corrects the listing to describe the shipped German-to-Portuguese dictionary only. The commit also removes the workstation-specific Android SDK path from the repository; the build uses `ANDROID_HOME` and was verified from `android/app` with no local SDK or signing properties.
