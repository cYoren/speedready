# TODO

Everything an agent can close is closed. What is left needs you: a signature, a merge request, a tag,
and one product decision. The reading work and its evidence live in
[the audit](docs/audit-2026-11-04.md); this file is only the handover.

Each step: why it matters, the command, what success looks like, what skipping costs.
Do them in this order: **1, 4, 2, 3**, and 5 whenever you decide. Step 2 refuses to build an untagged
version, and step 3's metadata has to name the tag from step 4.

## 1. Gloss packs: published already — verify, and do not re-upload the old cache

**Why.** Every language pair but de→pt needs a pack on the `packs` release; until it is there the app
says "no dictionary" for that pair. All 90 are published (assets built 2026-10-01, none dropped by the
quality gate).

**Command.**

```
gh release view packs --repo cYoren/speedready --json assets -q '.assets|length'
```

**Success:** `90`.

**Do not re-upload `~/.cache/speedready/packs-release`.** It is from 2026-09-22/23, before the 1.0.4
licence fix, and every pack in it still contains MUSE (CC BY-NC) rows (18,826 of them in
`gloss-de-pt` alone). Uploading that directory would republish non-commercial dictionary data and make
`DATA-LICENSES.md` false. The published assets were rebuilt on 2026-10-01 without them; confirm any one:

```
gh release download packs --repo cYoren/speedready --pattern gloss-de-pt.sqlite --dir /tmp/packs-check
sqlite3 /tmp/packs-check/gloss-de-pt.sqlite "select prio,count(*) from gloss group by prio"
rm -r /tmp/packs-check
```

**Success:** prio 1, 2 and 9 only — never 3. Only packs rebuilt by the current `tools/build_pack.py`
qualify.

**If skipped:** nothing breaks today. If the stale cache is uploaded instead, the licence statement in
`DATA-LICENSES.md` stops being true.

## 2. Create the release signing key and publish the APK

**Why.** F-Droid will not merge the app without a signed APK and the key's SHA-256 in the metadata.
The keystore is permanent: **if it is lost, this app can never be updated on F-Droid again, by
anyone.** Back it up in more than one place, and keep the password with it.

**Command.**

```
export JAVA_HOME=$(mise where java@temurin-21.0.12+101.0.LTS)   # Gradle 8.11 rejects the default JDK 26
tools/make_release_apk.sh
```

It creates `android/speedready.keystore` and `android/keystore.properties` (both gitignored), refuses
to build unless the tag from step 4 exists and bumped `versionCode`, then prints the
`gh release create` command and the `AllowedAPKSigningKeys:` line.

**Success:** the APK path, `versionName`, and a 64-character SHA-256; `apksigner verify` reports no
errors.

**If skipped:** no F-Droid APK, so step 3 cannot merge; Android users only get the Play build.

## 3. Update the F-Droid merge request

**Why.** The merge request at <https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884> is where
F-Droid decides what to build. Its description and metadata are older than this repository's: the
metadata here names `1.0.7` / commit `04bdfc1`, and all four of @seekme-seekyou's points are answered
in `packaging/submission/fdroid-mr-body.md`.

**Command.** Paste `packaging/submission/fdroid-mr-body.md` over the merge request description (it no
longer repeats version numbers: the metadata file is the one place that names them); then
put your new tag's `versionName`, `versionCode` and full commit hash into
`android/fdroid/io.github.cyoren.speedready.yml` (and the `AllowedAPKSigningKeys:` line from step 2),
copy that file into your fdroiddata fork as `metadata/io.github.cyoren.speedready.yml`, and push:

```
git clone https://gitlab.com/<you>/fdroiddata && cd fdroiddata   # <you> = the GitLab account that owns the MR
cp ~/Projects/speedready/android/fdroid/io.github.cyoren.speedready.yml metadata/io.github.cyoren.speedready.yml
git commit -am "io.github.cyoren.speedready: 1.0.9" && git push
```

Check it before pushing:

```
cd ~/Projects/speedready
python tools/check_release_tag.py --strict v1.0.9    # metadata, versionCode and commit must match the tag
```

**Success:** the merge request shows the new description and metadata, its pipeline (or the reviewer)
accepts the version/commit, and the app builds.

**If skipped:** the merge request stays on the old metadata and keeps the reading fixes out of F-Droid.

## 4. Tag the release F-Droid will build

**Why.** F-Droid's updater follows tags (`UpdateCheckMode: Tags`) and then compares `versionCode`. The
last tag it can act on is `v1.0.7` code 7; the tree is already `1.0.8` code 8, untagged. A tag without
a `versionCode` bump is found and ignored, which is why `tools/check_release_tag.py` (run by step 2)
refuses one — `v1.0.2` is the historical example.

**Command.** After this PR merges, on `master`, through the usual PR:

```
# 1. through a PR: bump android/app/build.gradle (versionCode 8 -> 9, versionName '1.0.8' -> '1.0.9')
#    and add fastlane/metadata/android/en-US/changelogs/9.txt; merge it
# 2. on master, at that merge commit:
git tag -a v1.0.9 -m "Speedready 1.0.9"
git push origin v1.0.9
python tools/check_release_tag.py v1.0.9
```

**Success:** `v1.0.9: versionName 1.0.9, versionCode 9 > 8 ... ok`, and F-Droid's next scan picks it
up with `CurrentVersion`/`CurrentVersionCode` matching in step 3.

**If skipped:** F-Droid keeps building the old commit, where `Buch` is glossed as "registrar, ganhar"
instead of "livro", and no reading fix after that commit ever reaches F-Droid users.

## 5. Decide how many language pairs the APK carries

**Why.** `web/bundle.json` names the one pair the website and the APK ship, so switching is one
command. Carrying more is a real trade, not a detail.

- **One pair (today).** The dictionary is bundled and reading needs no network. Cost: anyone learning
  another pair downloads 33 MB (desktop) or uses the website's pair; the APK carries ~8 MB of
  dictionary for one target language.
- **Several pairs, bundled.** Cost: roughly +8 MB per target pair in the APK, and the store listing's
  "works offline out of the box" stays true for all of them.
- **Several pairs, fetched at runtime.** Costs the permission-free claim: the manifest already asks for
  internet (book downloads), so this adds a download step on first use for those pairs, and F-Droid
  reviewers see a network feature. Do not add the permission just for this.

**Command** (only when you decide to switch the shipped pair):

```
/usr/bin/python3 tools/export_web.py de en --starter starter-de.json
```

**Success:** `web/bundle.json` names the new dictionary, and `/usr/bin/python3 tools/export_web.py --check`
reports the same agreement for that pair.

**If skipped:** nothing breaks. The current choice is deliberate and documented in the README.

## Closed since this file was written

- **6. Function words in every pair.** `core/` and its English pivot already fix `de→es wollen` →
  "querer", `sv→de är` → "ist; sind", `nl→pt is` → "é"; pinned by `tests/test_core.py`.
- **7. The web and desktop readers chose glosses differently.** `tools/export_web.py` now uses the
  desktop scorer; agreement over the starter book went from 94.43% to 99.87% of distinct words.
  Reproduce with `/usr/bin/python3 tools/export_web.py --check`.
- **8. The "same code" claim.** Already reworded: the readers are separate implementations sharing the
  data pipeline, and the F-Droid description no longer implies a download is needed for the bundled
  pair.
- **9. Tags that skip the `versionCode`.** `tools/check_release_tag.py`, run by step 2, and
  `tests/test_release_tag.py`.
