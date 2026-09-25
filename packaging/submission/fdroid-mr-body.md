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
  <br>`fastlane/metadata/android/en-US/` with title, short and full description, icon, three phone screenshots and changelogs for versionCode 1, 2 and 3.

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
  <br>Enabled. `Binaries` and `AllowedAPKSigningKeys` are set and the release APK is published.
  <br>The app is a WebView wrapper with no dependencies, `minifyEnabled false`, and `dependenciesInfo`
  disabled, so the build is deterministic. Measured on commit `a1e9772` (tag `v1.0.3`, JDK 21,
  Gradle 8.11.1 as pinned in the wrapper):
  <br>- two clean unsigned builds are byte-identical: `sha256 9e86f8cbf10d04d9209eb802c36486112e9753699e1f8370cc7ce08235f09daa`
  <br>- the published signed APK carries the same 21 non-signature zip entries, so only the signature differs
  <br>- published `speedready-1.0.3.apk` is `sha256 ffea8a78502f3ed7f825d403e8856ef2facf847bf35902e50e06483736a3307f`
  <br>The signing config only applies when a local `keystore.properties` is present, so a builder
  without one produces exactly the same unsigned APK from the same source.
* [x] Setup abi split if the APK is large and the splitted ones can be much smaller.
  <br>Not applicable: no native code, single ABI-independent APK.
* [x] Only the latest versions should be kept in the metadata before it's merged. If you update the metadata, please replace the old versions with the new ones.
  <br>One build entry, versionCode 3.
* [x] Don't add any disabled versions in the metadata.
* [x] The `commit` field should be the full hash. Please don't use tag or branch in commit.
  <br>`commit: a1e97725014bcbb5d862e0de401033ac0057aebe` (was `v1.0.1`).

### Pipeline

* [ ] All pipelines should pass.
  <br>Needs a maintainer to retrigger: the current pipeline ran zero jobs, so it stopped before
  reaching the build. Nothing has failed yet.
* [ ] All warnings and errors in the Reports tab should be fixed or explained.
  <br>Same status: no jobs have run, so there is nothing reported yet.
* [x] F-Droid CI runners are under GitLab's FOSS program, so there's no need for you to pay for any CI time. If Gitlab starts asking for phone numbers or credit cards don't submit anything, just leave a note in the MR so we know we need to trigger the CI.

---

Thanks for the review @seekme-seekyou. All four points are addressed:

1. Template followed above, with Reproducible Builds enabled.
2. `Binaries` and `AllowedAPKSigningKeys` added.
3. `Summary`, `Description` and `AutoName` removed from the yaml; they live in the upstream Fastlane folder.
4. `commit` is now the full hash.

Since the review the app has also cut a real Android release, tagged `v1.0.3` (`versionCode 3`).
The earlier metadata pointed at `v1.0.1`, which is why the build entry moved. While preparing it I
found and removed a genuine blocker: `android/local.properties` had been committed with
`sdk.dir=/home/gustvmar/Android/sdk`, a path that exists only on one workstation. A tracked
`local.properties` outranks `ANDROID_HOME`, so it would have pointed your builder at a directory
that does not exist. It is now gitignored and out of the tree.
