# Which language pairs the APK carries — the decision Gus has to make

Step 5 of the F-Droid handover. Nothing here is urgent: the current choice ships and works, and
`v1.0.10` is already published with it. This is about the *next* release.

Measured 13 November 2026 on the published `speedready-1.0.10.apk` (identical payload to 1.0.9); every size below was taken by
adding the file to a copy of that APK and re-measuring, not estimated.

## What the app ships today

| | |
|---|---|
| APK | 9.96 MB |
| the one bundled dictionary (`dict-de-pt.json`) | 8.2 MB raw, 1.6 MB inside the APK |
| the book catalogue (`catalog.json`) | 8.8 MB raw, 3.2 MB inside the APK |
| noun genders, all 10 languages (`genders-*.json`) | 25.6 MB raw, 4.4 MB inside the APK |
| readers with the bundled pair | offline, no download, no wait |
| readers with any other pair | one download on first use, then cached offline |

The German→Portuguese pair is bundled, so a German learner whose native language is Portuguese needs
no network. Everyone else — German→English being the obvious case — gets one download the first
time they open a book in that pair. That download already works today and is not gated by permission.

## The three options

### A. Keep one bundled pair (today)

**Cost:** 0 MB, 0 code. German→English readers still wait for a 2.8 MB download the first time.
**Benefit:** smallest APK, the current F-Droid build stays exactly as approved, and the store listing's
"your dictionary ships with it" claim is already true for the pair it names.
**Risk of the status quo:** the pair is de→pt, which is a narrower audience than de→en. The feature
that decides whether a German learner keeps the app (glosses without a wait) is behind a download for
most of them.

### B. Bundle several pairs

Measured, per pair added to the APK (compressed, inside the APK):

| pair added | APK becomes | increase |
|---|---:|---:|
| de→en | 12.73 MB | +2.77 MB |
| de→ru | 11.62 MB | +1.66 MB |
| es→en | 14.19 MB | +4.24 MB |
| **all nine de→X pairs** | **24.68 MB** | **+14.72 MB** |

**Cost:** the APK grows 1.7–4.2 MB per pair; all nine make it 24.68 MB (still well under Google
Play's limit and unremarkable for an offline reader).
**Benefit:** "works offline out of the box" stays literally true for every pair you bundle, with no
network feature for F-Droid reviewers to inspect and no first-use wait.
**Downside:** every user pays the download for pairs they will never read, and each bundled dictionary
is Wiktionary CC BY-SA data that now travels inside the APK, so `DATA-LICENSES.md` and the store's
data-safety answers have to keep naming it (they already do for the one).
**Effort:** a one-line change in the Android asset list plus the export step; the web reader keeps
fetching, so this is APK-only. A half hour plus a rebuild.

### C. Fetch every pair at runtime (bundle none)

**Cost:** the first book in *any* pair needs a 0.8–4.5 MB download (median 1.7 MB, de→en 2.8 MB),
de→pt included.
**Benefit:** the APK drops to ~8.4 MB and carries no Wiktionary-derived data at all, which makes the
licence story and the reproducible-build story simpler.
**Downside:** the app's "no network for the bundled pair" promise disappears entirely, and the F-Droid
description has to stop claiming it. Reviews see a network feature on the reading path — the kind of
thing F-Droid reviewers ask about. It also breaks reading on a plane for a brand-new install.
**Note:** no new permission is needed. `INTERNET` is already declared for book downloads, and the
handover is explicit that you do not add a permission just for this.

## Recommendation

**B, with de→en and de→ru added to the de→pt that ships today** — about +4.4 MB, a 14.4 MB APK.

Why: the app's whole pitch is reading a German book with instant glosses. Bundling de→en covers the
largest audience that is not already covered, de→ru the next, and the APK stays small enough that
nobody notices. It needs no new permission, adds no network feature for reviewers, and keeps the
store's offline claim true for the pairs most people use. C is the cleanest engineering answer and
the worst product one; A leaves the main feature behind a download for the majority.

## If you pick B (or C), the switch is

```
/usr/bin/python3 tools/export_web.py de en --starter starter-de.json
/usr/bin/python3 tools/export_web.py --check          # must report agreement for that pair
```

`web/bundle.json` names the pair and nothing else does; the website and the APK both follow it. For
several bundled pairs the Android asset list needs the extra `dict-*.json` files as well — that is the
one place this stops being a single command, and it is why the decision is a product one rather than
a mechanical one.

## What I did not do

I did not switch the pair. The handover says to recommend, not decide, and a wrong guess here changes
what every Android and web reader downloads. The measurements above are the evidence you need.
