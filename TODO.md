# TODO

Speedready 1.0.9 is tagged, signed and published. Two things are left, both needing you: one GitLab
push and the choice below. Everything I could run, I ran; the evidence is in the report.

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

## 4. Tag — done

`versionCode`/`versionName` were already 9 / `1.0.9` on master from #12, so the PR (#19) only added the
1.0.9 changelog, and the tag was made at that merge commit.

```
$ python tools/check_release_tag.py v1.0.9
v1.0.9: versionName 1.0.9, versionCode 9 > 7 at v1.0.7  ok
```

## 2. Signing key and APK — done

The key is not new. `v1.0.7`'s published APK carries SHA-256
`eeb938688a5078f4a1536abbd1020774a538bb01f0a7a874ef3e0c8240a5e361`, the fingerprint F-Droid's
metadata has named since 1.0.3, and the same key (identical keystore bytes) was already on this
workstation. Regenerating a key here would have silently made the app unupdatable on F-Droid forever,
so I installed the existing one and built with it.

```
APK:         android/app/build/outputs/apk/release/speedready-1.0.9.apk  (9.96 MB)
versionName: 1.0.9
SHA-256:     d468c5c8e512170c7f2310fad7c9a66f0bf2abd9b8070d33727c4ba4f530ea50
apksigner verify: Verifies, one signer, v2 scheme
```

Published: <https://github.com/cYoren/speedready/releases/tag/v1.0.9> — the asset's GitHub digest is
that same SHA-256.

**Still yours: the off-machine backup.** The keystore exists in two places today
(`~/Work/android-play-fixes/.signing/speedready.jks` and `/root/.hermes/secrets/speedready/` on
gaius, byte-identical). Both are machines that can die. Put a copy in the Bitwarden ops vault:
item name `android/speedready.keystore` (home-relative path, as the vault convention asks), password
next to it in the same note. Losing this file means no future Speedready update on F-Droid, by anyone,
ever.

## 3. F-Droid merge request — everything prepared, one push yours

The 1.0.9 build entry is in `android/fdroid/io.github.cyoren.speedready.yml` and passes:
`python tools/check_release_tag.py --strict v1.0.9` → ok, `fdroid lint` → no findings, and
`fdroid build io.github.cyoren.speedready:9` from that commit reproduces the unsigned APK byte for
byte (`f11db85d…`).

That last command is how I found and fixed two things that would have turned the pipeline red:

- `scanignore` listed one `.gz`; the repo now ships ten, and fdroidserver fails the build on each one
  it is not told to ignore (#22).
- `--strict` compared the metadata commit against the annotated tag's own object rather than its
  commit, so it could never pass; fixed, with a test (#20).

The two edits themselves are on GitLab, and there is no GitLab credential on this machine (no `glab`,
no token, and this SSH key is not in a GitLab account):

1. Paste `packaging/submission/fdroid-mr-body.md` over
   <https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884>.
2. Push `metadata/io.github.cyoren.speedready.yml` to the `speedready` branch of the
   `gustavo.cesar.marcelino4/fdroiddata` fork.

`packaging/submission/README.md` has the exact commands, and a clone with the commit already staged is
at `~/.cache/speedready/fdroiddata-fork/repo`.

## 5. Decide which language pairs the APK carries — yours, three options with costs

`docs/bundle-decision.md`, measured on the published 1.0.9 APK:

| option | APK | first-use download |
|---|---:|---|
| A. one pair (today, de→pt) | 9.96 MB | de→en readers wait for 2.8 MB |
| B. add de→en + de→ru | 14.39 MB (+4.43) | none for those three |
| C. fetch every pair | ~8.4 MB | every pair, de→pt included |

Recommendation: **B**. It needs no new permission, adds no network feature for reviewers, and keeps
"works offline out of the box" true for the pairs most readers use. Say B (or A, or C) and the switch
is one command plus, for B, an Android asset list edit.

## Closed earlier, kept for reference

Function words in every pair (`core/`, `tests/test_core.py`); one gloss scorer for web and desktop
(`tools/export_web.py --check`, 99.34% agreement); the "same code" wording; the release guard and its
test. The reading audit is `docs/audit-2026-11-04.md`.
