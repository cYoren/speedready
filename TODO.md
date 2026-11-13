# TODO

Speedready 1.0.10 is tagged, signed, published and verified by F-Droid's own build check. Three things
are left, all needing you: a GitLab push, a Play upload, and the pair decision.

The version is 1.0.10, not 1.0.9, because Play already shipped versionCode 9 on 2 November from a build
that predates the multilingual reading work. Reusing 9 would have made the reading release unreachable
for every Play user. Nothing else changed between the two: same tree, higher number.

## 1. Gloss packs — done, verified, not re-uploaded

```
$ gh release view packs --repo cYoren/speedready --json assets -q '.assets|length'
90
$ sqlite3 gloss-de-pt.sqlite "select prio,count(*) from gloss group by prio"
1|21877
2|43981
9|84774
```

prio 1, 2 and 9 only — no MUSE rows, so `DATA-LICENSES.md` stays true. The stale
`~/.cache/speedready/packs-release` was not touched.

## 4. Tag — done at `v1.0.10`

`versionCode 10` / `versionName '1.0.10'`, tagged at merge commit `0e4ea08`, changelog at
`fastlane/metadata/android/en-US/changelogs/10.txt`.

```
$ python tools/check_release_tag.py v1.0.10
v1.0.10: versionName 1.0.10, versionCode 10 > 9 at v1.0.9  ok
$ python tools/check_release_tag.py --strict v1.0.10
v1.0.10: versionName 1.0.10, versionCode 10 > 9 at v1.0.9  ok
```

## 2. Signing key and APK — done

The key is the one F-Droid has named since 1.0.3: `eeb938688a5078f4a1536abbd1020774a538bb01f0a7a874ef3e0c8240a5e361`.
Regenerating it would have made the app permanently unupdatable on F-Droid, so the existing keystore
was installed rather than created.

```
APK:         android/app/build/outputs/apk/release/speedready-1.0.10.apk  (9.96 MB)
versionName: 1.0.10   versionCode: 10
SHA-256:     9cb2f7a098ce1e7adea47dc4b3b361e361588ca44f2e327a3c972334a50d65f8
apksigner:   Verifies, one signer, eeb93868…
```

Published: <https://github.com/cYoren/speedready/releases/tag/v1.0.10>. The `v1.0.9` release was deleted
so nobody downloads a build that Play users can never match; its tag is left in place as history.

**Still yours: the off-machine backup.** The keystore exists in two places
(`~/Work/android-play-fixes/.signing/speedready.jks` and `/root/.hermes/secrets/speedready/` on gaius,
byte-identical). Both machines can die. Put a copy in the Bitwarden ops vault as
`android/speedready.keystore`, password in the same note. Lose it and Speedready can never be updated
on F-Droid again, by anyone.

## 3. F-Droid merge request — verified end to end, one push left

F-Droid's own tooling, run against fdroiddata's master config with fdroidserver 2.4.5:

```
$ fdroid lint io.github.cyoren.speedready
(no findings)
$ fdroid build io.github.cyoren.speedready:10
INFO: compared built binary to supplied reference binary successfully
INFO: supplied reference binary has allowed signer eeb938688a5078f4a1536abbd1020774a538bb01f0a7a874ef3e0c8240a5e361
INFO: success: io.github.cyoren.speedready
```

That is the whole reproducible-build check passing: it cloned the tag, rebuilt, compared bytes against
the published APK, and confirmed the signer. Two blockers had to be fixed to get there — `scanignore`
named one `.gz` when the repo ships ten (#22), and `--strict` compared the annotated tag object rather
than its commit (#20). Both have tests.

The remaining work is two edits on GitLab, which need a credential this machine does not have:

1. Paste `packaging/submission/fdroid-mr-body.md` over
   <https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884>.
2. Push `metadata/io.github.cyoren.speedready.yml` to the `speedready` branch of the
   `gustavo.cesar.marcelino4/fdroiddata` fork.

Exact commands are in `packaging/submission/README.md`; a clone with the commit already staged is at
`~/.cache/speedready/fdroiddata-fork/repo`.

## 4. Play Console — 1.0.10 needs uploading, and this is the important one

Play production is on versionCode 9 from 2 November: edge-to-edge and R8, **without** the multilingual
reading work. That is why the reading release has never reached Android users. `gplay release` with the
1.0.10 bundle is the step that fixes it.

```
gplay release --package io.github.cyoren.speedready --track production --bundle <1.0.10>.aab
```

Needs a bundle build (`gradle bundleRelease`) rather than the APK. I have not done this: it publishes
to production, which is your call, and it is the one step in this file that reaches real users.

## 5. Decide which language pairs the APK carries — yours

`docs/bundle-decision.md`, measured on the published APK:

| option | APK | first-use download |
|---|---:|---|
| A. one pair (today, de→pt) | 9.96 MB | de→en readers wait for 2.8 MB |
| B. add de→en + de→ru | 14.39 MB (+4.43) | none for those three |
| C. fetch every pair | ~8.4 MB | every pair, de→pt included |

Recommendation: **B**. No new permission, no network feature for reviewers, and "works offline out of
the box" stays true for the pairs most readers use. Say A, B or C.

## 6. iOS — still on 1.0.8, also without the reading work

`ios/` is at `MARKETING_VERSION 1.0.8`, `CURRENT_PROJECT_VERSION 8`, and does not reference
`web/reading.js`. The iOS app has the same gap as Play had. It needs a 1.0.10 (build 9) and a Mac to
sign, so it is outside anything this workstation can finish.
