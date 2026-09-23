Paste this over the description of https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884
(Edit → replace the body → Save). Everything below is already true of the branch except the two
lines marked TODO, which need `tools/make_release_apk.sh` to have been run first.

---

## Checklist

### Policy

* [x] The app complies with the [inclusion criteria](https://f-droid.org/docs/Inclusion_Policy).
* [x] The original app author has been notified (and does not oppose the inclusion). If you are not the author, please paste the link of the reply from the author.
  <br>I am the author.
* [x] The upstream app source code repo contains the app metadata in a [Fastlane](https://gitlab.com/snippets/1895688) or [Triple-T](https://gitlab.com/snippets/1901490) folder structure. The summary and description must be included and images, icon, and changelog should also be provided for better user experience. The `en-US` locale must be included.
  <br>`fastlane/metadata/android/en-US/` with title, short and full description, icon, three phone screenshots and changelogs for versionCode 1 and 2.

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
  <br>Fixed: `Summary`, `Description` and `AutoName` are removed; they come from the upstream Fastlane folder.
* [x] Releases are tagged and auto update is enabled unless there is a special reason.
  <br>`AutoUpdateMode: Version`, `UpdateCheckMode: Tags`.
* [x] There is an issue tracker and contact info of the author so that we can report bugs and contact the author.
* [x] An AuthorName must be added. It doesn't need to be the real name.
* [x] External repos are added as git submodules instead of srclibs. You can update git submodules without opening an MR in this repo and the submodule is covered by our scanner.
  <br>No external repos: the app has no dependencies at all (`dependencies { }`).
* [x] Enable [Reproducible Builds](https://f-droid.org/docs/Reproducible_Builds). We'll use your signature for improved security/reliability, also allowing users to switch between different channels. Do note that if you don't enable reproducible build then the apk will be signed with our key so you can't enable it later. If you can't enable this, please add the reasons here.
  <br>Enabled. `Binaries` and `AllowedAPKSigningKeys` are set. The app is a WebView wrapper with no
  dependencies and `minifyEnabled false`, and `dependenciesInfo` is disabled, so the build is
  deterministic. Building commit `243c884f` from a fresh `git worktree` at a different path, with no
  keystore present, gives the same unsigned APK as an in-place clean rebuild:
  `sha256 3b265f5be71cb5547f84fe39ca66208520e4283d5f47b53af8567fe0cd642da3` (JDK 21, AGP as pinned in the wrapper).
  The signing config is only applied when a local `keystore.properties` is present, so your builder
  produces exactly the same unsigned APK from the same source.
* [x] Setup abi split if the APK is large and the splitted ones can be much smaller.
  <br>Not applicable: no native code, single ABI-independent APK.
* [x] Only the latest versions should be kept in the metadata before it's merged. If you update the metadata, please replace the old versions with the new ones.
  <br>One build entry, versionCode 2. (Tag `v1.0.2` exists but is a desktop-only release; the Android
  versionCode and versionName are unchanged from `v1.0.1`, so it is deliberately not a new build entry.)
* [x] Don't add any disabled versions in the metadata.
* [x] The `commit` field should be the full hash. Please don't use tag or branch in commit.
  <br>Fixed: `commit: 243c884fd3142162c12d24b133e35e344ec71bfe` (was `v1.0.1`).

### Pipeline

* [ ] All pipelines should pass.
* [ ] All warnings and errors in the Reports tab should be fixed or explained.
* [x] F-Droid CI runners are under GitLab's FOSS program, so there's no need for you to pay for any CI time. If Gitlab starts asking for phone numbers or credit cards don't submit anything, just leave a note in the MR so we know we need to trigger the CI.

---

Thanks for the review @seekme-seekyou. All four points are addressed:

1. Template followed above, with Reproducible Builds enabled.
2. `Binaries` and `AllowedAPKSigningKeys` added.
3. `Summary` and `Description` removed from the yaml (and `AutoName` with them); they live in the upstream Fastlane folder.
4. `commit` is now the full hash.
