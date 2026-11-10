# Speedready

Pacer and RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita with a shared web reader for mobile and browsers.

- **Pacer**: the whole text on screen, a highlight sweeps through at your pace, read words dim behind it
- **RSVP**: one word (or chunk) flashed at a time with a red pivot letter
- First-run language setup; the interface and translation target follow the learner's language (English and Brazilian Portuguese UI)
- Select text in the pacer and send the phrase to DeepL or Google Translate. In beginner mode, long-press the first word and tap the last one
- Click a word to continue from there. Double-click it for a dictionary popup (lemmatized; en.wiktionary glosses plus the Duden meanings for German, browser button for the full page); close it and the flow resumes from that word
- Right-click a word you don't know: it gets a subtle underline everywhere it occurs and the pacer lingers on it. Your list lives in `unknown.txt`
- `P` reads the current sentence aloud (piper TTS, offline, voice downloaded on first use); the popup has a pronounce button
- `A` read-along: piper reads sentence by sentence and the highlight follows the voice. WPM sets the speech speed
- Chapter list from the epub's TOC (works around broken anchors by finding the headings in the text)
- Every lookup lands in `~/.config/speedready/vocab.tsv` with its sentence, importable into Anki as-is
- Remembers your position, WPM, chunk size, reading mode, beginner mode, and read-along setting per book; progress is saved atomically while you read
- Bookmarks are stored per book (`B` toggles one, `Shift+B` opens the list)
- **Library** (`L`): every book you have opened, newest first, with how far through it you are. Add several at once from the file picker, or drag epub and txt files straight onto the window. Titles come from the epub's own metadata, so the list reads like a shelf and not like a download folder
- Everything is configurable in the settings dialog (fonts, colours, pauses, chunk size, dictionaries)

## Install (Linux, GTK4 + libadwaita + python-gobject)

```
./install.sh        # venv with simplemma + piper-tts, launcher + icon
./run.sh book.epub  # or open "Speedready" from your app launcher
```

## Keys

| key | action |
|---|---|
| space | play / pause |
| ← → | ±10 words |
| PageUp / PageDown | ±one page |
| ↑ ↓ | speed ±5 (shift: ±25) |
| [ ] | words per step |
| M | pacer / rsvp |
| R | replay sentence |
| D | define current word |
| click / double-click / right-click | continue from there / dictionary popup / mark unknown |
| P | speak from here to the end of the sentence, again to stop |
| A | read-along |
| B / Shift+B | toggle bookmark / open bookmarks |
| C | chapters |
| L | library |
| F11, S, O | fullscreen, settings, open |

## Dictionary packs

Beginner mode glosses each word from an offline pack, `gloss-<src>-<tgt>.sqlite`, which the app
downloads once per language pair on first use. The packs are built from English Wiktionary and each
language's own Wiktionary edition (kaikki.org) and hermitdave/FrequencyWords.
See [DATA-LICENSES.md](DATA-LICENSES.md) for upstream licence and attribution details.

```
python tools/fetch_sources.py            # ~2 GB of extracts -> ~/.cache/speedready/build
python tools/release_packs.py --jobs 6   # build every pair, measure, keep the good ones
python tools/release_packs.py --upload   # gh release upload to the "packs" release
```

A pack is only published if it glosses at least half of the 2000 commonest words in its source
language (`--min-coverage`). Pairs below the floor are dropped rather than shipped, because a pack
that exists but glosses nothing would have the app report the dictionary ready over a page of blank
glosses. An unpublished pair is reported as such in the app.
MUSE-free pack build, 2026-09-25: all 90 language pairs passed the 50% threshold. Median coverage
was 92.1%; best was sv->en at 96.7%, worst ru->nl at 54.8%. Total size was 4.66 GB. These
figures come from `tools/release_packs.py` measured against each pair's top 2,000 source words.

Content words are reliable across every pair. The commonest grammar words often are not: Wiktionary
picks the wrong homograph for them (`sv->de` gives `är` as "Gut, Ware", `nl->pt` gives `is` as
"seu"). `core/` fixes these for every pair: each source language's ~300 commonest words are checked
once in English and pivoted through English into every target (`coreglosses.py`), so `de->es wollen`
is "querer", `sv->de är` is "ist; sind" and `nl->pt is` is "é". `GLOSS_OVERRIDES` in `speedready.py`
keeps the hand-curated de->pt glosses, which are more idiomatic than the pivot.

## German noun genders

In German books every noun is colored by gender: blue for der, red for die, green for das (Settings → Deutsch).
`gender.py` holds the logic, with no GTK code so a browser extension can port it line for line. It takes the
gender from the article in front (`die stille See` is the sea, `der See` the lake), splits unknown compounds
(`Hahnenfeder` → `Feder`), colors plurals by their singular, and leaves pronouns, names, plural-only nouns and
ambiguous sentence-initial words alone. `web/gender.js` is the same logic for the web reader, and `web/textclean.js` is the book cleanup; `tests/test_web_parity.py`
fails if the Python and JavaScript versions ever disagree (`PYTHONPATH=. python tests/test_web_parity.py *.epub` checks real books). The data, `web/genders-de.json.gz` (0.6 MB, noun form → genders), comes from
the kaikki.org English Wiktionary extract:

```
python tools/build_genders.py ~/.cache/speedready/build/en-German.jsonl.gz
python gender.py   # self-check
```

The web reader and the Chrome extension also color nouns in Spanish, French, Italian, Portuguese, Russian,
Polish, Dutch (de/het) and Swedish (en/ett): `Gender.tag()` in `web/gender.js`. There a word is a noun when the
Wiktionary data says so; a spelling that is also a common other word (`est`, `parte`) is only colored after an
article, which also picks between two genders. Each language's data, `web/genders-<lang>.json.gz` (0.2 to 0.8 MB),
loads the first time a book in that language opens. `tests/test_gender_languages.py` checks one sentence each.

```
python tools/build_genders_more.py   # all eight, from the same kaikki.org extracts
```

## Web version (any phone or browser)

`web/` is a self-contained reader for learners, and it is also what the Android and iOS
apps load: a book in any of 10 languages with a translation in your own language above
every word you have not marked as known yet. Tap a translation to mark the word learned
and it disappears everywhere; tap a word for its dictionary entry. Books you add stay in
a library (the apps can also scan a folder for books and let you pick which to add). The
interface is in all 10 languages. It ships with a public-domain German book, speaks
through the device's own voice, and works offline once loaded (installable to the home
screen). It is a separate implementation from the desktop reader; they share the data
pipeline (`tools/export_web.py`, `coreglosses.py`), not the reading code.

`core/` holds hand-checked glosses for each language's ~300 most frequent words, which a
context-free dictionary gets wrong most often. `/usr/bin/python3 tools/export_web.py --patch <dict files>`
writes them into exported dictionaries; pairs without English go through English.

Read-along drives the highlight from its own estimated clock rather than from
`onboundary`, which iOS reports unreliably, and re-syncs whenever a boundary event does
arrive. Devices with no speech voices installed say so instead of failing silently.

Build its data from a desktop pack:

```
/usr/bin/python3 tools/export_web.py de pt      # -> web/dict-de-pt.json (8.2 MB, ~1.5 MB gzipped)
/usr/bin/python3 tools/export_web.py --check    # web reader vs desktop reader, over the starter book
```

The exported glosses are the ones the desktop reader would show: `tools/export_web.py` calls
`speedready.pick_gloss`, the same scoring `Gloss.raw` uses, so the two readers weigh exact case,
part of speech and frequency identically instead of the web taking the highest-priority row.
`--check` prints the agreement over the bundled starter book and fails below 99%. Build against the
published pack (`gh release download packs --pattern gloss-de-pt.sqlite`), not a cache left over from
before 1.0.4: those carry MUSE data, which is never exported.

The shipped language pair is named in `web/bundle.json` and nowhere else; `index.html` and `sw.js`
both read it, and the reader takes its source language from the dictionary's own `src` field. So
changing which pair the website and the Android APK carry is that one command plus a starter book,
with no code edit. A test enforces it: neither file may name a dictionary or a language again.

One APK still ships one pair, because that dictionary is bundled: the shipped pair reads offline
with no download. The app's one permission is internet, used to fetch another language pair or a
free book, never to measure what you read. Shipping several pairs means either a bigger APK or
network access, which is a trade worth making deliberately.

## iPhone and iPad app

`ios/` is a native shell around `web/`, the same way `android/` is: the page does the reading, and
`ios/Speedready/App.swift` serves it offline from the app bundle and adds dialogs, the Anki export via the
share sheet, links out to Safari, and speech that plays with the silent switch on. It needs iOS 16.4+
(the offline dictionary unpacks with `DecompressionStream`).

```
open ios/Speedready.xcodeproj                      # run in the simulator from Xcode
ASC_KEY_PATH=… ASC_KEY_ID=… ASC_ISSUER=… ios/release.sh   # signed .ipa for App Store Connect, from Terminal on the Mac
```

Create the app record (bundle id `io.github.cyoren.speedready`) in App Store Connect before the first upload.

## Read in any language and find free books

Reading languages are independent of the interface and the ten optional dictionary languages.
EPUB language metadata is preserved, including three-letter ISO codes; use the book-language
field to correct it. Enter a code such as `ar`, `ja`, `zh`, or `fil`. Arabic and Hebrew read
right to left. Chinese, Japanese, Thai, and other scripts without spaces are segmented into
reading units (browser `Intl.Segmenter`; system ICU on Linux, with a character fallback).
Existing positions for books in spaced scripts keep their original indices. Dictionary and
speech availability still depend on the installed language pair and device voices.

In **Books → Download free books**, search the bundled Project Gutenberg catalog by title,
author, and any catalog language. Downloads are saved in the library and reopen offline.
The Linux library has the same **Download free books** button. Linux downloads keep the
original EPUB/text file in `~/.local/share/speedready/books/` and reuse it on later downloads.
The catalog snapshot includes 78,461 texts across 68 languages; availability depends on the source.

**Other open libraries** links to Standard Ebooks, Wikisource, and Open Book Publishers.
Import their downloaded files with **Add books**, or paste a direct EPUB/PDF/text URL from
Gutenberg, Standard Ebooks, or Open Book Publishers in the web reader (EPUB/text on Linux).
Direct downloads are limited to 30 MB. Books retain their own licenses; check the source terms.

The official Gutenberg CSV is cached locally by `tools/build_catalog.py`; building again
reuses it. To deliberately refresh the catalog snapshot:

```bash
cd ~/Projects/speedready
python tools/build_catalog.py --refresh
```

The website uses `api/book.js` to download selected books from approved HTTPS hosts, because
Gutenberg does not allow cross-origin browser downloads. It rejects arbitrary hosts, unsafe
redirects, oversized downloads, and HTML error pages. Deploy both `web/` and the root `api/`
function with the repository's Vercel configuration. Packaged mobile apps/extensions use
`https://speedready.vercel.app/api/book`; their direct downloads require this function to be
published there. The Linux reader downloads from the sources directly.

For a local preview with working downloads (Node 24+):

```bash
cd ~/Projects/speedready
node --use-env-proxy tools/serve.cjs
```

Open `http://127.0.0.1:8765` in a browser. Verification:

```bash
cd ~/Projects/speedready
/usr/bin/python3 -m unittest discover -s tests -q
node tests/reading.cjs
/usr/bin/python3 tools/export_web.py --check    # web and desktop readers agree on the starter book
```

Before tagging a release, run the guard F-Droid needs: a tag that does not bump Android's
`versionCode` is found by the `Tags` updater and then ignored, so it never reaches Android users.

```
python tools/check_release_tag.py v1.0.9        # --strict also compares the fdroiddata metadata
tools/make_release_apk.sh                       # runs the guard before it builds
```

## Audit and release checks

The [4 November 2026 audit](docs/audit-2026-11-04.md) records fixes, measurements,
regression coverage, and the device/deployment checks still required before release.
The download endpoint streams books with a 30 MB bound. EPUB import validates ZIP
entries and bounds expanded text; the catalog builds a reusable search index.

Additional local checks:

```bash
cd ~/Projects/speedready
node tests/catalog.cjs
node tests/downloads.cjs
```

`tests/browser_audit.cjs` exercises synthetic imports, long-book reading, storage
failures, keyboard and touch controls, both themes, accessibility, and offline reopening.
It requires an existing Playwright installation/browser and a cached axe-core 4.10.3
script (`AXE_PATH` can select it); it does not download books from public sources.
`PLAYWRIGHT_MODULE`, `CHROMIUM`, and `AUDIT_URL` can select local tooling and the preview URL.
Screenshots and the JSON result are saved under the ignored `dist/audit/` directory.
