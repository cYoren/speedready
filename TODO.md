# TODO

Things that still need a human, and things deliberately left undone. Written 2026-09-23.

## Needs you specifically

### 1. Publish the gloss packs

All 90 pairs are built and sitting in `~/.cache/speedready/packs-release` (4.5 GB, none dropped by
the quality gate). Until they are uploaded, every pair except de→pt reports "no dictionary" in the
app, which is honest but not useful.

```
python tools/release_packs.py --upload
```

This creates the `packs` release on cYoren/speedready and uploads all 90. `PACK_URL` in
`speedready.py` already points at it.

### 2. Create the release signing key and publish the APK

Needed for the F-Droid reproducible build. **The keystore is permanent: if it is lost, this app can
never be updated on F-Droid again, by anyone.** Back it up in more than one place.

```
export JAVA_HOME=$(mise where java@temurin-21.0.12+101.0.LTS)   # Gradle 8.11 rejects the default JDK 26
tools/make_release_apk.sh
```

It creates the keystore, builds, signs, and prints two things: the `gh release create` command, and
the `AllowedAPKSigningKeys:` line to paste into `android/fdroid/io.github.cyoren.speedready.yml`
(currently a commented placeholder).

### 3. Update the F-Droid merge request

Paste `packaging/submission/fdroid-mr-body.md` over the description of
<https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884>, then copy the fixed
`android/fdroid/io.github.cyoren.speedready.yml` into your fdroiddata fork's
`metadata/io.github.cyoren.speedready.yml` and push.

All four of @seekme-seekyou's points are addressed in the file already.

## Decisions waiting on you

### 4. Tag a release so F-Droid ships the noun fix

F-Droid builds commit `243c884f` (tag `v1.0.1`), which predates the web lookup fix. As it stands,
the first F-Droid users get `Buch` glossed as "registrar, ganhar" instead of "livro".

To fix, before the MR merges:

- bump `versionCode` 2 → 3 and `versionName` to `1.0.3` in `android/app/build.gradle`
- add `fastlane/metadata/android/en-US/changelogs/3.txt`
- tag `v1.0.3`, and set the metadata's `versionName`, `versionCode` and full `commit` hash to match
- rerun `tools/make_release_apk.sh` and upload that APK to the `v1.0.3` release

Not done here because the version number and the timing against an in-review MR are yours to pick.

### 5. One APK still ships one language pair

`web/bundle.json` now decides which pair the website and the APK carry, so switching is one command.
Carrying *several* is a real trade: the dictionary is bundled and the app requests no permissions at
all, which is a selling point in the store listing. More pairs means either a much bigger APK or
adding `INTERNET` and downloading packs. Worth deciding rather than drifting into.

## Known gaps, not bugs

### 6. Grammar words are only curated for de→pt

`GLOSS_OVERRIDES` in `speedready.py` hand-corrects ~200 high-frequency function words, because a
context-free dictionary reliably picks the wrong sense for them. It covers `('de','pt')` only, so
every other pair inherits the raw Wiktionary answer:

```
de→es  wollen = "de lana"      (woollen, not "to want")
sv→de  är     = "Gut, Ware"    (the noun vara, not "is")
nl→pt  is     = "seu"
```

Content words are fine everywhere; it is the commonest ~50 words that are wrong. The cheap fix is to
curate the list once for de→en and pivot it through each target's Wiktionary, since knowing that
`wollen` means "want" does not depend on the target language. `build_pack.py` already has the pivot
machinery (prio 2).

### 7. The web reader and the desktop reader are two implementations

They share the data pipeline (`export_web.py` imports `GLOSS_OVERRIDES` and `Gloss.short` from
`speedready.py`) but not the reading logic, and that logic drifted: the noun/verb lookup bug existed
in the web reader for its whole life and never in the desktop one. Agreement over the starter book
is now 93.3%; the remaining gap is `export_web.py` choosing glosses by priority alone while
`Gloss.raw` also weighs part of speech and word frequency.

Porting that scorer into `export_web.py` would close most of it and is the highest-value cleanup
left. It means regenerating `web/dict-de-pt.json`, so it wants a careful before/after check.

### 8. The README claims the readers are the same code

> "The reader is the same code that runs as a desktop application on Linux."

This is in `README.md` and in `fastlane/metadata/android/en-US/full_description.txt`, which is the
F-Droid store description. It is not true: they are parallel implementations sharing data. Worth
rewording before the store listing goes live.

### 9. `UpdateCheckMode: Tags` cannot see Android-only changes

The Android `versionCode` did not change between `v1.0.1` and `v1.0.2`, so F-Droid's updater finds
the new tag and correctly does nothing. That is right today, but it means any future tag that
forgets to bump `versionCode` will silently never reach Android users.
